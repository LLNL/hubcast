import sys
import traceback

import aiohttp
from aiohttp import web
from attrs import define, field
from gidgethub import aiohttp as gh_aiohttp
from gidgethub import sansio
from typing import Dict

from .auth.github import App
from .routes.github import router


@define
class AppCache:
    _apps: Dict[str, App] = field()

    def get_app(self, app_id: str, config: dict) -> App:
        if not self._apps[app_id]:
            self._apps[app_id] = App(
                id=app_id,
                requester=config["requester"],
                url=config["repo"],
                private_key_path=config["private_key_path"],
            )

        return self._apps[app_id]


_app_cache = AppCache()


async def github(
    request: web.Request, github_config: dict, git_config: dict
) -> web.Response:
    try:
        app = _app_cache.get_app(github_config["app_id"], github_config)

        # read the GitHub webhook payload
        body = await request.read()

        event = sansio.Event.from_http(
            request.headers, body, secret=github_config["secret"]
        )
        print("GH delivery ID", event.delivery_id, file=sys.stderr)

        # retrieve GitHub authentication token
        token = await app.authenticate_installation()

        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(
                session, github_config["requester"], oauth_token=token
            )

            # call the appropriate callback for the event
            await router.dispatch(event, gh, git_config, session=session)

        # return a "Success"
        return web.Response(status=200)

    except Exception:
        traceback.print_exc(file=sys.stderr)
        return web.Response(status=500)
