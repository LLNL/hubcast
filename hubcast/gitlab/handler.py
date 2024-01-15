import sys
import traceback

import aiohttp
from aiohttp import web
from gidgethub import aiohttp as gh_aiohttp
from gidgetlab import aiohttp as gl_aiohttp
from gidgetlab import sansio

from .routes import router


class GitLabHandler:
    def __init__(self, auth, requester, webhook_secret, gh_requester, gh_auth):
        self.auth = auth
        self.requester = requester
        self.webhook_secret = webhook_secret
        self.gh_requester = gh_requester
        self.gh_auth = gh_auth

    async def handle(self, request):
        try:
            # read the GitLab webhook payload
            body = await request.read()

            event = sansio.Event.from_http(
                request.headers, body, secret=self.webhook_secret
            )
            print("GL delivery ID", event.event, file=sys.stderr)

            # retrieve GitLab authentication token
            gl_token = await self.auth.authenticate_installation(None)

            # retrieve GitHub authentication token
            gh_token = await self.gh_auth.authenticate_installation(
                "alecbcs", "hubcast-testing"
            )

            async with aiohttp.ClientSession() as session:
                gh = gh_aiohttp.GitHubAPI(
                    session, self.gh_requester, oauth_token=gh_token
                )
                gl = gl_aiohttp.GitLabAPI(
                    session, self.requester, access_token=gl_token
                )

                # call the appropriate callback for the event
                await router.dispatch(event, gh, gl, session=session)

                # return a "Success"
                return web.Response(status=200)

        except Exception:
            traceback.print_exc(file=sys.stderr)
            return web.Response(status=500)
