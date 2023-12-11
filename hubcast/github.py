import os
import sys
import traceback

import aiohttp
from aiohttp import web
from gidgethub import aiohttp as gh_aiohttp
from gidgethub import sansio

from .auth.github import authenticate_installation, get_installation_id
from .routes.github import router

# Get configuration from environment
GH_SECRET = os.environ.get("HC_GH_SECRET")
GH_REQUESTER = os.environ.get("HC_GH_REQUESTER")


async def github(request):
    try:
        # read the GitHub webhook payload
        body = await request.read()

        event = sansio.Event.from_http(request.headers, body, secret=GH_SECRET)
        print("GH delivery ID", event.delivery_id, file=sys.stderr)

        # get installation id for configured repostitory
        installation_id = await get_installation_id()

        # retrieve GitHub authentication token
        token = await authenticate_installation(installation_id)

        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(session, GH_REQUESTER, oauth_token=token)

            # call the appropriate callback for the event
            await router.dispatch(event, gh, session=session)

        # return a "Success"
        return web.Response(status=200)

    except Exception:
        traceback.print_exc(file=sys.stderr)
        return web.Response(status=500)
