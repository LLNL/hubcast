import os
from aiohttp import web, ClientSession
from gidgethub import aiohttp as gh_aiohttp
from gidgetlab import aiohttp as gl_aiohttp

from .auth.github import get_installation_id, authenticate_installation
from .config import settings
from .github import github
from .gitlab import gitlab
from .models import GitHubConfig, GitLabConfig, HubcastRepoCache
from .utils.git import Git


repo_cache = HubcastRepoCache()
git = Git(config=settings.git.to_dict())


def make_github_client(
    session: ClientSession, github_config: GitHubConfig
) -> gh_aiohttp.GitHubAPI:
    # get installation id for configured repostitory
    if not github_config.installation_id:
        github_config.installation_id = await get_installation_id(github_config)

    # retrieve GitHub authentication token
    gh_token = await authenticate_installation(github_config)

    return gh_aiohttp.GitHubAPI(
        session, github_config.requester, oauth_token=gh_token
    )


def make_gitlab_client(
    session: ClientSession, gitlab_config: GitLabConfig
) -> gl_aiohttp.GitLabAPI:
    return gl_aiohttp.GitLabAPI(
        session, gitlab_config.requester, access_token=gitlab_config.access_token
    )


async def main(request) -> web.Response:
    # suggested to use a single session for the lifetime of the application
    # to take advantage of connection pooling
    # see: https://docs.aiohttp.org/en/stable/client_reference.html#client-session
    async with ClientSession() as session:
        repo = repo_cache.get(name=settings.repo.name, config=settings.to_dict())
        gh = make_github_client(session, repo.github_config)

        # route request to github or gitlab submodule based on event type header
        if "x-github-event" in request.headers:
            return await github(session, request, repo, gh)
        elif "x-gitlab-event" in request.headers:
            gl = make_gitlab_client(session, repo.gitlab_config)
            return await gitlab(session, request, repo, gh, gl)
        else:
            return web.Response(status=404)


if __name__ == "__main__":
    print("Initializing hubcast ...")
    print("Configuring Git Repository ...")
    if not os.path.exists(settings.git.base_path):
        os.makedirs(settings.git.base_path)
        git("init")
        git(f"remote add github {settings.github.url}")
        git(f"remote add gitlab {settings.gitlab.url}")

    print("Starting Web Server...")
    app = web.Application()
    app.router.add_post("/", main)

    web.run_app(app, port=settings.hubcast.port)
