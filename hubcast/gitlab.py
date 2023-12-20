import os
import sys
import traceback

import aiohttp
from aiohttp import web
from gidgethub import aiohttp as gh_aiohttp
from gidgetlab import aiohttp as gl_aiohttp
from gidgetlab import sansio

from .auth.github import authenticate_installation, get_installation_id
from .routes.gitlab import router

# Get configuration from environment
GH_REQUESTER = os.environ.get("HC_GH_REQUESTER")
GL_ACCESS_TOKEN = os.environ.get("HC_GL_ACCESS_TOKEN")
GL_SECRET = os.environ.get("HC_GL_SECRET")
GL_REQUESTER = os.environ.get("HC_GL_REQUESTER")


async def gitlab(request):
    try:
        # read the GitLab webhook payload
        body = await request.read()

        event = sansio.Event.from_http(request.headers, body, secret=GL_SECRET)
        print("GL delivery ID", event.event, file=sys.stderr)

        # get installation id for configured repostitory
        gh_installation_id = await get_installation_id()

        # retrieve GitHub authentication token
        gh_token = await authenticate_installation(gh_installation_id)

        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(session, GH_REQUESTER, oauth_token=gh_token)
            gl = gl_aiohttp.GitLabAPI(session, GL_REQUESTER, access_token=GL_ACCESS_TOKEN)

            # call the appropriate callback for the event
            await router.dispatch(event, gh, gl, session=session)

        # return a "Success"
        return web.Response(status=200)

    except Exception:
        traceback.print_exc(file=sys.stderr)
        return web.Response(status=500)
