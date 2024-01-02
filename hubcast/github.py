import sys
import traceback

from aiohttp import web, ClientSession
from gidgethub import sansio
from gidgethub import aiohttp as gh_aiohttp

from .models import HubcastRepo
from .routes.github import router


async def github(
    session: ClientSession,
    request: web.Request,
    repo: HubcastRepo,
    gh: gh_aiohttp.GitHubAPI,
) -> web.Response:
    try:
        # read the GitHub webhook payload
        body = await request.read()

        event = sansio.Event.from_http(
            request.headers, body, secret=repo.github_config.secret
        )
        print("GH delivery ID", event.delivery_id, file=sys.stderr)

        # call the appropriate callback for the event
        await router.dispatch(event, repo, gh, session=session)

        # return a "Success"
        return web.Response(status=200)

    except Exception:
        traceback.print_exc(file=sys.stderr)
        return web.Response(status=500)
