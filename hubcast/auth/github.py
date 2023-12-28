import os
import re
import time

import aiohttp
import gidgethub.apps as gha
from attrs import define, field
from gidgethub import aiohttp as gh_aiohttp
from typing import Awaitable, Dict, Tuple

#: location for authenticated app to get a token for one of its installations
INSTALLATION_TOKEN_URL = "app/installations/{installation_id}/access_tokens"


@define
class GitHubAuthException(Exception):
    message: str = field()


@define
class MissingConfigException(GitHubAuthException):
    pass


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


@define
class App:
    id: str = field()
    requester: str = field()
    url: str = field()
    private_key_path: str = field()
    owner: str = field()
    repo: str = field()
    private_key: str = field()
    installation_id: str = field(default=None)

    # TODO: The owner and repo attributes assume ssh style urls
    @owner.default
    def _owner(self):
        return re.search(r"(?<=\:)[^\/]*", self.url, re.IGNORECASE).group()

    @repo.default
    def _repo(self):
        return re.search(r"(?<=\/)[^.]*", self.url, re.IGNORECASE).group()

    @private_key.default
    def _private_key(self) -> str:
        """Load private key from file."""

        # TODO: jwt seems to require a private key--confirm if this should fail early
        if not os.path.exists(self.private_key_path):
            raise MissingConfigException(
                f"Unable to find private key for app {self.id} at {self.private_key_path}"
            )

        with open(self.private_key_path, "r") as handle:
            return handle.read()

    async def get_jwt(self) -> str:
        """Get a JWT from cache, creating a new one if necessary."""

        async def renew_jwt() -> Tuple[int, str]:
            # GitHub requires that you create a JWT signed with the application's
            # private key. You need the app id and the private key, and you can
            # use this gidgethub method to create the JWT.
            now = time.time()
            jwt = gha.get_jwt(app_id=self.id, private_key=self.private_key)

            # gidgethub JWT's expire after 10 minutes (you cannot change it)
            return (now + 10 * 60), jwt

        return await _tokens.get_token("JWT", renew_jwt)

    async def get_installation_id(self) -> str:
        if not self.installation_id:
            async with aiohttp.ClientSession() as session:
                gh = gh_aiohttp.GitHubAPI(session, self.requester)

                result = await gh.getitem(
                    f"/repos/{self.owner}/{self.repo}/installation",
                    accept="application/vnd.github+json",
                    jwt=await self.get_jwt(),
                )

                self.installation_id = result["id"]

        return self.installation_id

    async def authenticate_installation(self) -> str:
        """Get an installation access token for the application.
        Renew the JWT if necessary, then use it to get an installation access
        token from github, if necessary.
        """

        installation_id = await self.get_installation_id()

        async def renew_installation_token() -> Tuple[int, str]:
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

                expires = parse_isotime(result["expires_at"])
                token = result["token"]
                return (expires, token)

        return await _tokens.get_token(installation_id, renew_installation_token)
