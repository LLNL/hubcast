import logging

import aiohttp
from aiohttp import web
from gidgethub import aiohttp as gh_aiohttp
from gidgetlab import sansio

from hubcast.github.auth import GitHubAuthenticator
from hubcast.gitlab.routes import router

logger = logging.getLogger(__name__)


class GitLabHandler:
    """ """

    gh_auth: GitHubAuthenticator
    gh_requester: str
    webhook_secret: str

    def __init__(
        self,
        gh_authenticator: GitHubAuthenticator,
        gh_requester: str,
        webhook_secret: str,
    ):
        self.gh_auth = gh_authenticator
        self.gh_requester = gh_requester
        self.webhook_secret = webhook_secret

    async def handle(self, request: web.Request):
        try:
            # read the GitLab webhook payload
            body = await request.read()
            event = sansio.Event.from_http(
                request.headers, body, secret=self.webhook_secret
            )
            logger.warning(f"GL delivery ID: {event.event}")

            # get coorisponding GitHub repo owner and name from event
            # request variables
            gh_repo_owner = request.rel_url.query["gh_owner"]
            gh_repo = request.rel_url.query["gh_repo"]
            gh_check_name = request.rel_url.query["gh_check"]

            # retrieve GitHub authentication token
            gh_token = await self.gh_auth.authenticate_installation(
                gh_repo_owner, gh_repo
            )

            async with aiohttp.ClientSession() as session:
                gh = gh_aiohttp.GitHubAPI(
                    session, self.gh_requester, oauth_token=gh_token
                )

                # call the appropriate callback for the event
                await router.dispatch(
                    event, gh, gh_repo_owner, gh_repo, gh_check_name, session=session
                )

                # return a "Success"
                return web.Response(status=200)

        except Exception as exc:
            logger.exception(exc)
            return web.Response(status=500)
