import logging
import sys

from aiohttp import web
from aiojobs.aiohttp import setup

from hubcast.account_map.file import FileMap
from hubcast.clients.github import GitHubClientFactory
from hubcast.clients.gitlab import GitLabClientFactory
from hubcast.config import Config
from hubcast.web.github import GitHubHandler
from hubcast.web.gitlab import GitLabHandler


def main():
    app = web.Application()
    conf = Config()

    if conf.account_map_type == "file":
        account_map = FileMap(conf.account_map_path)
    else:
        print("Error: No Account Map Type Found")
        sys.exit(1)

    gh_client_factory = GitHubClientFactory(
        conf.gh.app_id, conf.gh.privkey, conf.gh.requester
    )
    gl_client_factory = GitLabClientFactory(
        conf.gl.instance_url,
        conf.gl.access_token,
        conf.gl.callback_url,
        conf.gl.webhook_secret,
    )

    gh_handler = GitHubHandler(
        conf.gh.webhook_secret,
        account_map,
        gh_client_factory,
        gl_client_factory,
    )

    gl_handler = GitLabHandler(
        conf.gl.webhook_secret,
        gh_client_factory,
    )

    app.router.add_post("/v1/events/src/github", gh_handler.handle)
    app.router.add_post("/v1/events/dest/gitlab", gl_handler.handle)

    logging.basicConfig(level=logging.INFO)

    setup(app)
    web.run_app(app, port=conf.port)


if __name__ == "__main__":
    main()
