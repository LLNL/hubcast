import os
from aiohttp import web

from .config import settings
from .github import github
from .gitlab import gitlab
from .utils.git import Git


github_settings = settings.github.to_dict()
git_settings = settings.git.to_dict()
git = Git(config=git_settings)


async def main(request) -> web.Response:
    # route request to github or gitlab submodule based on event type header
    if "x-github-event" in request.headers:
        return await github(request, github_settings, git_settings)
    elif "x-gitlab-event" in request.headers:
        return await gitlab(request)
    else:
        return web.Response(status=404)


if __name__ == "__main__":
    print("Initializing hubcast ...")
    print("Configuring Git Repository ...")
    if not os.path.exists(settings.git.repo_path):
        os.makedirs(settings.git.repo_path)
        git("init")
        git(f"remote add github {settings.github.repo}")
        git(f"remote add gitlab {settings.gitlab.repo}")

    print("Starting Web Server...")
    app = web.Application()
    app.router.add_post("/", main)

    web.run_app(app, port=settings.hubcast.port)
