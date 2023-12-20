import os
from aiohttp import web

from .github import github
from .gitlab import gitlab
from .utils.git import git

# Get configuration from environment
GIT_REPO_PATH = os.environ.get("HC_GIT_REPO_PATH")
GH_REPO = os.environ.get("HC_GH_REPO")
GL_REPO = os.environ.get("HC_GL_REPO")
PORT = os.environ.get("HC_PORT")


async def main(request):
    # route request to github or gitlab submodule based on event type header
    if "x-github-event" in request.headers:
        return await github(request)
    elif "x-gitlab-event" in request.headers:
        return await gitlab(request)
    else:
        return web.Response(status=404)


if __name__ == "__main__":
    print("Initializing hubcast ...")
    print("Configuring Git Repository ...")
    if not os.path.exists(GIT_REPO_PATH):
        os.makedirs(GIT_REPO_PATH)
        git("init")
        git(f"remote add github {GH_REPO}")
        git(f"remote add gitlab {GL_REPO}")

    print("Starting Web Server...")
    app = web.Application()
    app.router.add_post("/", main)
    if PORT is not None:
        PORT = int(PORT)

    web.run_app(app, port=PORT)
