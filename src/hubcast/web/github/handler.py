import logging

from aiohttp import web
from aiojobs.aiohttp import spawn
from gidgethub import sansio

from .routes import router

log = logging.getLogger(__name__)


class GitHubHandler:
    def __init__(
        self, webhook_secret, account_map, github_client_factory, gitlab_client_factory
    ):
        self.webhook_secret = webhook_secret
        self.account_map = account_map
        self.gh = github_client_factory
        self.gl = gitlab_client_factory

    async def handle(self, request):
        try:
            # read the GitHub webhook payload
            body = await request.read()
            event = sansio.Event.from_http(
                request.headers, body, secret=self.webhook_secret
            )

            log.info(f"GH delivery ID: {event.delivery_id}")

            try:
                github_user = event.data["sender"]["login"]
                gitlab_user = self.account_map(github_user)
            except Exception as exc:
                log.error(exc)
                return web.Response(status=200)

            if gitlab_user is None:
                log.info(f"Unauthorized GitHub User: {github_user}")
                return web.Response(status=200)

            gh_repo_owner = event.data["repository"]["owner"]["login"]
            gh_repo = event.data["repository"]["name"]

            gh = self.gh.create_client(gh_repo_owner, gh_repo)
            gl = self.gl.create_client(gitlab_user)

            await spawn(request, router.dispatch(event, gh, gl, gitlab_user))

            # return a "Success"
            return web.Response(status=200)

        except Exception:
            return web.Response(status=500)
