import json
import logging
import logging.config
import os
import sys

from aiohttp import web
from aiojobs.aiohttp import setup

from hubcast.account_map.file import FileMap, FileMapError
from hubcast.clients.github import GitHubClientFactory
from hubcast.clients.gitlab import GitLabClientFactory, GitLabSrcClientFactory
from hubcast.config import Config, ConfigError
from hubcast.web.github import GitHubHandler
from hubcast.web.gitlab import GitLabHandler, GitLabSrcHandler

log = logging.getLogger(__name__)


def main():
    app = web.Application()

    try:
        conf = Config()
    except ConfigError as exc:
        log.error(exc)
        sys.exit(1)

    if os.path.exists(conf.logging_config_path):
        try:
            with open(conf.logging_config_path) as f:
                logging_config = json.load(f)
            logging.config.dictConfig(logging_config)
        except (
            json.decoder.JSONDecodeError,
            # calls to logging.config.dictConfig will raise the following exceptions (cf stdlib docs):
            ValueError,
            TypeError,
            AttributeError,
            ImportError,
        ) as exc:
            log.error(exc)
            sys.exit(1)
    else:
        logging.basicConfig(level=logging.INFO)

    # error if we're unable to initialize an account map
    if conf.account_map_type == "file":
        try:
            account_map = FileMap(conf.account_map_path)
        except FileMapError:
            log.exception("Error initializing file account map")
            sys.exit(1)
    else:
        log.error(
            "Unknown account map type",
            extra={"account_map_type": conf.account_map_type},
        )
        sys.exit(1)

    # destination can only be gitlab
    dest_client_factory = GitLabClientFactory(
        conf.gl_dest.instance_url,
        conf.gl_dest.access_token,
        conf.gl_dest.callback_url,
        conf.gl_dest.webhook_secret,
    )

    if conf.src_service == "github":
        src_client_factory = GitHubClientFactory(
            conf.gh_src.app_id, conf.gh_src.privkey, conf.gh_src.requester
        )
        src_handler = GitHubHandler(
            conf.gh_src.webhook_secret,
            account_map,
            src_client_factory,
            dest_client_factory,
        )

    elif conf.src_service == "gitlab":
        src_client_factory = GitLabClientFactory(
            conf.gl_dest.instance_url,
            conf.gl_dest.requester,
            conf.gl_dest.token,
            conf.gl_dest.callback_url,
            conf.gl_dest.webhook_secret,
            conf.gl_dest.token_type,
        )
        src_client_factory = GitLabSrcClientFactory(
            conf.gl_src.instance_url, conf.gl_src.access_token, conf.gl_src.requester
        )

        src_handler = GitLabSrcHandler(
            conf.gl_src.webhook_secret,
            account_map,
            src_client_factory,
            dest_client_factory,
        )

    # destination can only be gitlab
    dest_handler = GitLabHandler(
        conf.gl_dest.webhook_secret,
        src_client_factory,
    )

    log.info("Starting HTTP server")

    app.router.add_post(f"/v1/events/src/{conf.src_service}", src_handler.handle)
    app.router.add_post("/v1/events/dest/gitlab", dest_handler.handle)

    setup(app)
    web.run_app(
        app,
        port=conf.port,
        access_log_format='"%r" %s %b "%{Referer}i" "%{User-Agent}i"',
    )


if __name__ == "__main__":
    main()
