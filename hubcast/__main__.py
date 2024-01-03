import os
from aiohttp import web, ClientSession
from gidgethub import aiohttp as gh_aiohttp
from gidgetlab import aiohttp as gl_aiohttp

from .auth.github import get_installation_id, authenticate_installation
from .config import settings
from .github import github
from .gitlab import gitlab
from .models import GitHubConfig, GitLabConfig, HubcastRepo, HubcastRepoCache
from .utils.git import Git


repo_cache = HubcastRepoCache()


async def make_github_client(
    session: ClientSession, github_config: GitHubConfig
) -> gh_aiohttp.GitHubAPI:
    # get installation id for configured repostitory
    if not github_config.installation_id:
        github_config.installation_id = await get_installation_id(github_config)

    # retrieve GitHub authentication token
    gh_token = await authenticate_installation(github_config)

    return gh_aiohttp.GitHubAPI(session, github_config.requester, oauth_token=gh_token)


def make_gitlab_client(
    session: ClientSession, gitlab_config: GitLabConfig
) -> gl_aiohttp.GitLabAPI:
    return gl_aiohttp.GitLabAPI(
        session, gitlab_config.requester, access_token=gitlab_config.access_token
    )


def init_git_repo(repo: HubcastRepo):
    print(f"Initializing git repository for {repo.name} at {repo.git_repo_path}")
    git = Git(base_path=repo.git_repo_path)
    git("init")
    git(f"remote add github {repo.github_config.url}")
    git(f"remote add gitlab {repo.gitlab_config.url}")


async def main(request) -> web.Response:
    # TODO: move main handler to closure to house session for app lifetime
    # suggested to use a single session for the lifetime of the application
    # to take advantage of connection pooling
    # see: https://docs.aiohttp.org/en/stable/client_reference.html#client-session
    async with ClientSession() as session:
        repo = repo_cache.get(name=settings.repo.name, config=settings.to_dict())

        if not os.path.exists(repo.git_repo_path):
            os.makedirs(repo.git_repo_path)
            init_git_repo(repo)

        gh = await make_github_client(session, repo.github_config)

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

    print("Starting Web Server...")
    app = web.Application()
    app.router.add_post("/", main)

    web.run_app(app, port=settings.hubcast.port)
