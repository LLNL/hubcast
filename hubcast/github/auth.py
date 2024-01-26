import time
from typing import Awaitable, Callable, Dict, Tuple

import aiohttp
import gidgethub.apps as gha
from gidgethub import aiohttp as gh_aiohttp

#: location for authenticated app to get a token for one of its installations
INSTALLATION_TOKEN_URL = "app/installations/{installation_id}/access_tokens"


class TokenCache:
    """
    Cache for web tokens with an expiration.
    """

    def __init__(self) -> None:
        self._tokens = {}

    async def get_token(
        self,
        name: str,
        renew: Callable[[], Awaitable[Tuple[float, str]]],
        time_needed: int = 60,
    ) -> str:
        """
        Get a cached token, or renew as needed.

        Parameters
        ---------
        name: str
            An identifying name of a token to get from the cache.
        renew: Callable[None]
            A function to call in order to generate a new token if the cache
            is stale.
        time_needed: int
            The length of time a token will be needed. Thus any token that
            expires during this window should be disregarded and renewed.
        """
        expires, token = self._tokens.get(name, (0, ""))

        now = time.time()
        if expires < now + time_needed:
            expires, token = await renew()
            self._tokens[name] = (expires, token)

        return token


class GitHubAuthenticator:
    """
    An authenticator and token handler for GitHub.

    Attributes:
    ----------
    requester: str
        A GitHub bot user to act as and perform actions as.
    private_key: str
        A pem encoded string of the GitHub App's private key
        which is used to generate JWTs and other access tokens.
    app_id: str
        A string of the numeric GitHub App's ID.
    """

    def __init__(self, requester: str, private_key: str, app_id: str) -> None:
        self.requester = requester
        self.private_key = private_key
        self.app_id = app_id
        self._tokens = TokenCache()
        self._id_dict = {}

    async def get_installation_id(self, owner: str, repo: str) -> str:
        if (owner, repo) not in self._id_dict:
            async with aiohttp.ClientSession() as session:
                gh = gh_aiohttp.GitHubAPI(session, self.requester)
                result = await gh.getitem(
                    f"/repos/{owner}/{repo}/installation",
                    accept="application/vnd.github+json",
                    jwt=await self.get_jwt(),
                )
                self._id_dict[(owner, repo)] = result["id"]

        return self._id_dict[(owner, repo)]

    async def authenticate_installation(self, owner: str, repo: str) -> str:
        """
        Get an installation access token for the application.
        Renew the JWT if necessary, then use it to get an installation access
        token from github, if necessary.
        """
        installation_id = await self.get_installation_id(owner, repo)

        async def renew_installation_token():
            async with aiohttp.ClientSession() as session:
                gh = gh_aiohttp.GitHubAPI(session, self.requester)

                # Use the JWT to get a limited-life OAuth token for a particular
                # installation of the app. Note that we get a JWT only when
                # necessary -- when we need to renew the installation token.
                result = await gh.post(
                    INSTALLATION_TOKEN_URL,
                    {"installation_id": installation_id},
                    data=b"",
                    accept="application/vnd.github.machine-man-preview+json",
                    jwt=await self.get_jwt(),
                )

                expires = self.parse_isotime(result["expires_at"])
                token = result["token"]
                return (expires, token)

        return await self._tokens.get_token(installation_id, renew_installation_token)

    def parse_isotime(self, timestr: str) -> int:
        """Convert UTC ISO 8601 time stamp to seconds in epoch"""
        if timestr[-1] != "Z":
            raise ValueError(f"Time String '{timestr}' not in UTC")
        return int(time.mktime(time.strptime(timestr[:-1], "%Y-%m-%dT%H:%M:%S")))

    async def get_jwt(self) -> str:
        """Get a JWT from cache, creating a new one if necessary."""

        async def renew_jwt() -> Tuple[float, str]:
            # GitHub requires that you create a JWT signed with the application's
            # private key. You need the app id and the private key, and you can
            # use this gidgethub method to create the JWT.
            now = time.time()
            jwt = gha.get_jwt(app_id=self.app_id, private_key=self.private_key)

            # gidgethub JWT's expire after 10 minutes (you cannot change it)
            return (now + 10 * 60), jwt

        return await self._tokens.get_token("JWT", renew_jwt)
