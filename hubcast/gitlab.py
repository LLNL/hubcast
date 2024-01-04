import sys
import traceback

from aiohttp import web, ClientSession
from gidgetlab import sansio
from gidgethub import aiohttp as gh_aiohttp
from gidgetlab import aiohttp as gl_aiohttp

from .models import HubcastRepo
from .routes.gitlab import router


async def gitlab(
    session: ClientSession,
    request: web.Request,
    repo: HubcastRepo,
    gh: gh_aiohttp.GitHubAPI,
    gl: gl_aiohttp.GitLabAPI,
) -> web.Response:
    try:
        # read the GitLab webhook payload
        body = await request.read()

        event = sansio.Event.from_http(
            request.headers, body, secret=repo.gitlab_config.secret
        )
        print("GL delivery ID", event.event, file=sys.stderr)

        # call the appropriate callback for the event
        await router.dispatch(event, repo, gh, gl, session=session)

        # return a "Success"
        return web.Response(status=200)

    except Exception:
        traceback.print_exc(file=sys.stderr)
        return web.Response(status=500)
