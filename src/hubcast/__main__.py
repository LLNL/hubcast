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
        # TODO go back and consolidate the src* classes into src and dest

        # unless impersonation tokens are used for the src (which doesn't make sense, because we want the src to have a bot handler, not a human)
        # using a requester makes no sense, as all other gitlab tokens will behave as a bot (requester/user won't mean anything in calls to authenticate with GL)
        # https://docs.gitlab.com/user/project/settings/project_access_tokens/#bot-users-for-projects
        # the alternative is creating a bot user in gitlab, assigning it access to different projects/groups
        # and generating a personal access token for that bot -- however, this means projects can't install the app, they'd have to request access
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

    # TODO why do these routes need to end in the name of the service?
    app.router.add_post(f"/v1/events/src/{conf.src_service}", src_handler.handle)
    app.router.add_post("/v1/events/dest/gitlab", dest_handler.handle)

    logging.basicConfig(level=logging.INFO)

    setup(app)
    web.run_app(app, port=conf.port)


if __name__ == "__main__":
    main()
