import logging
import sys

from aiohttp import web
from aiojobs.aiohttp import setup

from hubcast.account_map.file import FileMap
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
    except ConfigError as e:
        log.error(e)
        sys.exit(1)

    # error if we're unable to initialize an account map
    if conf.account_map_type == "file":
        account_map = FileMap(conf.account_map_path)
    else:
        log.error(f"Error: Unknown Account Map Type: {conf.account_map_type}")
        sys.exit(1)

    # destination can only be gitlab
    dest_client_factory = GitLabClientFactory(
        conf.gl_dest.instance_url,
        conf.gl_dest.access_token,
        conf.gl_dest.callback_url,
        conf.gl_dest.webhook_secret,
    )

    if conf.src_forge == "github":
        src_client_factory = GitHubClientFactory(
            conf.gh_src.app_id, conf.gh_src.privkey, conf.gh_src.requester
        )
        src_handler = GitHubHandler(
            conf.gh_src.webhook_secret,
            account_map,
            src_client_factory,
            dest_client_factory,
        )

    elif conf.src_forge == "gitlab":
        # TODO if bot users are implemented requester is the bot access token is the api-level token that is provided by the user
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

    app.router.add_post(f"/v1/events/src/{conf.src_forge}", src_handler.handle)
    app.router.add_post("/v1/events/dest/gitlab", dest_handler.handle)

    logging.basicConfig(level=logging.INFO)

    setup(app)
    web.run_app(app, port=conf.port)


if __name__ == "__main__":
    main()
