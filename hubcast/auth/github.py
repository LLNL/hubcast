import time

import aiohttp
import gidgethub.apps as gha
from attrs import define, field
from gidgethub import aiohttp as gh_aiohttp
from typing import Awaitable, Dict, Tuple

from hubcast.models import GitHubConfig

#: location for authenticated app to get a token for one of its installations
INSTALLATION_TOKEN_URL = "app/installations/{installation_id}/access_tokens"


@define
class TokenCache:
    """
    Cache for web tokens with an expiration.
    """

    _tokens: Dict[str, Tuple[int, str]] = field(factory=dict)

    async def get_token(
        self, name: str, renew: Awaitable, *, time_needed: int = 60
    ) -> str:
        """Get a cached token, or renew as needed."""
        expires, token = self._tokens.get(name, (0, ""))

        now = time.time()
        if expires < now + time_needed:
            expires, token = await renew()
            self._tokens[name] = (expires, token)

        return token


#: Cache of web tokens for the app
_tokens = TokenCache()


def parse_isotime(timestr) -> int:
    """Convert UTC ISO 8601 time stamp to seconds in epoch"""
    if timestr[-1] != "Z":
        raise ValueError(f"Time String '{timestr}' not in UTC")
    return int(time.mktime(time.strptime(timestr[:-1], "%Y-%m-%dT%H:%M:%S")))


async def get_jwt(github_config: GitHubConfig) -> str:
    """Get a JWT from cache, creating a new one if necessary."""

    async def renew_jwt() -> Tuple[int, str]:
        # GitHub requires that you create a JWT signed with the application's
        # private key. You need the app id and the private key, and you can
        # use this gidgethub method to create the JWT.
        now = time.time()
        jwt = gha.get_jwt(
            app_id=github_config.app_id, private_key=github_config.private_key
        )

        # gidgethub JWT's expire after 10 minutes (you cannot change it)
        return (now + 10 * 60), jwt

    return await _tokens.get_token("JWT", renew_jwt)


async def get_installation_id(
    session: aiohttp.ClientSession, github_config: GitHubConfig
) -> str:
    gh = gh_aiohttp.GitHubAPI(session, github_config.requester)

    result = await gh.getitem(
        f"/repos/{github_config.owner}/{github_config.repo}/installation",
        accept="application/vnd.github+json",
        jwt=await get_jwt(github_config),
    )

    return result["id"]


async def authenticate_installation(
    session: aiohttp.ClientSession, github_config: GitHubConfig
) -> str:
    """Get an installation access token for the application.
    Renew the JWT if necessary, then use it to get an installation access
    token from github, if necessary.
    """

    async def renew_installation_token() -> Tuple[int, str]:
        gh = gh_aiohttp.GitHubAPI(session, github_config.requester)

        # Use the JWT to get a limited-life OAuth token for a particular
        # installation of the app. Note that we get a JWT only when
        # necessary -- when we need to renew the installation token.
        result = await gh.post(
            INSTALLATION_TOKEN_URL,
            {"installation_id": github_config.installation_id},
            data=b"",
            accept="application/vnd.github.machine-man-preview+json",
            jwt=await get_jwt(github_config),
        )

        expires = parse_isotime(result["expires_at"])
        token = result["token"]
        return (expires, token)

    return await _tokens.get_token(
        github_config.installation_id, renew_installation_token
    )
