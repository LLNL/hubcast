from aiohttp import web, ClientSession
from gidgethub import aiohttp as gh_aiohttp
from gidgetlab import aiohttp as gl_aiohttp

from .auth.github import get_installation_id, authenticate_installation
from .config import settings
from .github import github
from .gitlab import gitlab
from .models import HubcastRepoCache


repo_cache = HubcastRepoCache()


async def main(request) -> web.Response:
    # TODO: move main handler to closure to house session for app lifetime
    # suggested to use a single session for the lifetime of the application
    # to take advantage of connection pooling
    # see: https://docs.aiohttp.org/en/stable/client_reference.html#client-session
    async with ClientSession() as session:
        repo = repo_cache.get(name=settings.repo.name, config=settings.to_dict())

        if not repo.github_config.installation_id:
            repo.github_config.installation_id = await get_installation_id(repo.github_config)

        # retrieve GitHub authentication token
        gh_token = await authenticate_installation(repo.github_config)

        gh = gh_aiohttp.GitHubAPI(session, repo.github_config.requester, oauth_token=gh_token)

        # route request to github or gitlab submodule based on event type header
        if "x-github-event" in request.headers:
            return await github(session, request, repo, gh)
        elif "x-gitlab-event" in request.headers:
            gl = gl_aiohttp.GitLabAPI(
                session, repo.gitlab_config.requester, access_token=repo.gitlab_config.access_token
            )
            return await gitlab(session, request, repo, gh, gl)
        else:
            return web.Response(status=404)


if __name__ == "__main__":
    print("Initializing hubcast ...")

    print("Starting Web Server...")
    app = web.Application()
    app.router.add_post("/", main)

    web.run_app(app, port=settings.hubcast.port)
