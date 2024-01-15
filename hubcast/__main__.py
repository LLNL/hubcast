import os
from typing import Any
from urllib.parse import urlparse

from aiohttp import web

from hubcast.account_map.file import FileMap
from hubcast.github.auth import GitHubAuthenticator
from hubcast.github.handler import GitHubHandler
from hubcast.gitlab.auth import GitLabAuthenticator
from hubcast.gitlab.handler import GitLabHandler


class HubcastForwarder:
    """
    An event forwarder to route between GitHub and GitLab handlers based on
    event headers.

    Attributes:
    ----------
    github: GitHubHandler
        A GitHub webhook event handler.
    gitlab: GitLabHandler
        A GitLab webhook event handler.
    """

    def __init__(self, github_handler: GitHubHandler, gitlab_handler: GitLabHandler):
        self.github = github_handler
        self.gitlab = gitlab_handler

    async def handle(self, request: web.Request) -> Any:
        """
        Routes a request to either the GitHub or GitLab handler based on
        request headers.

        Parameters
        ----------
        request: web.Request
            A web request of event data from GitHub or GitLab.

        """
        if "x-github-event" in request.headers:
            return await self.github.handle(request)
        if "x-gitlab-event" in request.headers:
            return await self.gitlab.handle(request)
        return web.Response(status=404)


def main():
    print("Initializing hubcast ...")
    repos_path = os.environ.get("HC_REPOS_PATH")
    port = os.environ.get("HC_PORT")
    if port is not None:
        port = int(port)

    account_map_path = os.environ.get("HC_ACCOUNT_FILE")

    gh_app_id = os.environ.get("HC_GH_APP_IDENTIFIER")
    gh_privkey = os.environ.get("HC_GH_PRIVATE_KEY")
    gh_requester = os.environ.get("HC_GH_REQUESTER")
    gh_webhook_secret = os.environ.get("HC_GH_SECRET")

    gl_instance_url = os.environ.get("HC_GL_URL")
    gl_access_token = os.environ.get("HC_GL_ACCESS_TOKEN")
    gl_requester = os.environ.get("HC_GL_REQUESTER")
    gl_webhook_secret = os.environ.get("HC_GL_SECRET")

    github_auth = GitHubAuthenticator(gh_requester, gh_privkey, gh_app_id)
    gitlab_auth = GitLabAuthenticator(gl_instance_url, gl_access_token)

    parsed = urlparse(account_map_path)
    if parsed.scheme in ("file", ""):
        account_map = FileMap(account_map_path)
    # else:
    # account_map = ServerMap(account_map_path)

    github_handler = GitHubHandler(
        github_auth,
        gh_requester,
        gh_webhook_secret,
        repos_path,
        account_map,
        gitlab_auth,
        gl_instance_url,
    )

    gitlab_handler = GitLabHandler(github_auth, gh_requester, gl_webhook_secret)

    hubcast = HubcastForwarder(github_handler, gitlab_handler)

    print("Configuring Temporary Repositories Directory ...")
    if not os.path.exists(repos_path):
        os.makedirs(repos_path)

    print("Starting Web Server...")
    app = web.Application()
    app.router.add_post("/", hubcast.handle)

    web.run_app(app, port=port)


if __name__ == "__main__":
    main()
