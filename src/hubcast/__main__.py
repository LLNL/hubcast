import logging
import sys

from aiohttp import web
from aiojobs.aiohttp import setup

from hubcast.account_map.file import FileMap
from hubcast.clients.github import GitHubClientFactory
from hubcast.clients.gitlab import GitLabClientFactory
from hubcast.config import Config, ConfigError
from hubcast.web.github import GitHubHandler
from hubcast.web.gitlab import GitLabHandler

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
        conf.gl.instance_url,
        conf.gl.access_token,
        conf.gl.callback_url,
        conf.gl.webhook_secret,
    )

    if conf.src_service == "github":
        src_client_factory = GitHubClientFactory(
            conf.gh.app_id, conf.gh.privkey, conf.gh.requester
        )
        src_handler = GitHubHandler(
            conf.gh.webhook_secret,
            account_map,
            src_client_factory,
            dest_client_factory,
        )

    elif conf.src_service == "gitlab":
        # TODO this needs to be modified to allow for source commands
        src_client_factory = GitLabClientFactory(
            conf.gl.instance_url,
            conf.gl.access_token,
            conf.gl.callback_url,
            conf.gl.webhook_secret,
        )

        src_handler = GitLabHandler(
            conf.gl.webhook_secret,
            src_client_factory,
            # TODO does this need to have dest here?
        )
    else:
        log.error('the source service can only be one of "gitlab" or "github"')
        sys.exit(1)

    # destination can only be gitlab
    dest_handler = GitLabHandler(
        conf.gl.webhook_secret,
        src_client_factory,
    )

    # TODO why do these routes need to end in the name of the service?
    app.router.add_post(f"/v1/events/src/{conf.src_service}", src_handler.handle)
    app.router.add_post("/v1/events/dest/gitlab", dest_handler.handle)

    logging.basicConfig(level=logging.INFO)

    setup(app)
    web.run_app(app, port=conf.port)


if __name__ == "__main__":
    main()
