import logging
import sys
import traceback

from aiohttp import web
from aiojobs.aiohttp import spawn
from gidgetlab import sansio

from hubcast.clients.github import GitHubClientFactory
from hubcast.clients.gitlab import GitLabSrcClientFactory

from .routes import router

log = logging.getLogger(__name__)


class GitLabHandler:
    def __init__(
        self,
        webhook_secret: str,
        src_client_factory: GitHubClientFactory | GitLabSrcClientFactory,
    ):
        self.webhook_secret = webhook_secret
        self.src_client_factory = src_client_factory

    async def handle(self, request):
        try:
            # read the GitLab webhook payload
            body = await request.read()
            event = sansio.Event.from_http(
                request.headers, body, secret=self.webhook_secret
            )
            log.info(f"GL delivery ID: {event.event}")

            src_forge = request.rel_url.query["src_forge"]
            src_check_name = request.rel_url.query["src_check_name"]

            # get corresponding GitHub repo owner and name from event request variables
            # create_client takes different args depending on the forge
            # required webhook data in the query args also depends on the forge
            if src_forge == "github":
                src_repo_name = request.rel_url.query["src_repo_name"]
                src_repo_owner = request.rel_url.query["src_owner"]
                src_client = self.src_client_factory.create_client(
                    src_repo_owner, src_repo_name
                )
            elif src_forge == "gitlab":
                src_repo_id = request.rel_url.query["src_repo_id"]
                src_client = self.src_client_factory.create_client(src_repo_id)
            else:
                log.warning(f"invalid src forge {src_forge}")

            await spawn(
                request,
                router.dispatch(event, src_forge, src_client, src_check_name),
            )

            # return a "Success"
            return web.Response(status=200)

        except Exception:
            traceback.print_exc(file=sys.stderr)
            return web.Response(status=500)


class GitLabSrcHandler:
    def __init__(
        self, webhook_secret: str, account_map, src_client_factory, dest_client_factory
    ):
        self.webhook_secret = webhook_secret
        self.account_map = account_map
        self.src = src_client_factory
        self.dest = dest_client_factory

    async def handle(self, request):
        try:
            # read the GitLab webhook payload
            body = await request.read()
            event = sansio.Event.from_http(
                request.headers, body, secret=self.webhook_secret
            )

            log.info(f"GL delivery ID: {event.event}")
            try:
                # the Push Hook provides user_username
                # the Merge Request Hook provides user["username"]
                # they are equivalent -- can verify with the user ID or avatar URL
                src_user = event.data.get("user", {}).get("username") or event.data.get(
                    "user_username"
                )
                dest_user = self.account_map(src_user)
            except Exception as exc:
                log.error(exc)
                return web.Response(status=200)

            if dest_user is None:
                log.info(f"Unauthorized user: {src_user}")
                return web.Response(status=200)

            src_repo_id = event.data["project"]["id"]

            gl_src = self.src.create_client(src_repo_id)
            gl_dest = self.dest.create_client(dest_user)

            await spawn(
                request,
                router.dispatch(event, gl_src, gl_dest, dest_user),
            )

            # return a "Success"
            return web.Response(status=200)

        except Exception:
            traceback.print_exc(file=sys.stderr)
            return web.Response(status=500)
