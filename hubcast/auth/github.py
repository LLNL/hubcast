import os
import re
import time

import aiohttp
import gidgethub.apps as gha
from gidgethub import aiohttp as gh_aiohttp

# get config from environment.
GH_REPO = os.environ.get("HC_GH_REPO")
GH_REQUESTER = os.environ.get("HC_GH_REQUESTER")
GH_PRIVATE_KEY_PATH = os.environ.get("HC_GH_PRIVATE_KEY_PATH")
GH_APP_IDENTIFIER = os.environ.get("HC_GH_APP_IDENTIFIER")

# load private key from file if provided.
if os.path.exists(GH_PRIVATE_KEY_PATH):
    with open(GH_PRIVATE_KEY_PATH, "r") as handle:
        GH_PRIVATE_KEY = handle.read()

#: location for authenticated app to get a token for one of its installations
INSTALLATION_TOKEN_URL = "app/installations/{installation_id}/access_tokens"


class TokenCache:
    """
    Cache for web tokens with an expiration.
    """

    def __init__(self):
        # token name to (expiration, token) tuple
        self._tokens = {}

    async def get_token(self, name, renew, *, time_needed=60):
        """Get a cached token, or renew as needed."""
        expires, token = self._tokens.get(name, (0, ""))

        now = time.time()
        if expires < now + time_needed:
            expires, token = await renew()
            self._tokens[name] = (expires, token)

        return token


#: Cache of web tokens for the app
_tokens = TokenCache()


async def authenticate_installation(installation_id):
    """Get an installation access token for the application.
    Renew the JWT if necessary, then use it to get an installation access
    token from github, if necessary.
    """

    async def renew_installation_token():
        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(session, GH_REQUESTER)

            # Use the JWT to get a limited-life OAuth token for a particular
            # installation of the app. Note that we get a JWT only when
            # necessary -- when we need to renew the installation token.
            result = await gh.post(
                INSTALLATION_TOKEN_URL,
                {"installation_id": installation_id},
                data=b"",
                accept="application/vnd.github.machine-man-preview+json",
                jwt=await get_jwt(),
            )

            expires = parse_isotime(result["expires_at"])
            token = result["token"]
            return (expires, token)

    return await _tokens.get_token(installation_id, renew_installation_token)


def parse_isotime(timestr):
    """Convert UTC ISO 8601 time stamp to seconds in epoch"""
    if timestr[-1] != "Z":
        raise ValueError(f"Time String '{timestr}' not in UTC")
    return int(time.mktime(time.strptime(timestr[:-1], "%Y-%m-%dT%H:%M:%S")))


async def get_jwt():
    """Get a JWT from cache, creating a new one if necessary."""

    async def renew_jwt():
        # GitHub requires that you create a JWT signed with the application's
        # private key. You need the app id and the private key, and you can
        # use this gidgethub method to create the JWT.
        now = time.time()
        jwt = gha.get_jwt(app_id=GH_APP_IDENTIFIER, private_key=GH_PRIVATE_KEY)

        # gidgethub JWT's expire after 10 minutes (you cannot change it)
        return (now + 10 * 60), jwt

    return await _tokens.get_token("JWT", renew_jwt)


class IDStore:
    def __init__(self):
        self.id = None
        self.owner = re.search(r"(?<=\:)[^\/]*", GH_REPO, re.IGNORECASE).group()
        self.repo = re.search(r"(?<=\/)[^.]*", GH_REPO, re.IGNORECASE).group()

    async def get_id(self):
        if self.id is None:
            async with aiohttp.ClientSession() as session:
                gh = gh_aiohttp.GitHubAPI(session, GH_REQUESTER)

                result = await gh.getitem(
                    f"/repos/{self.owner}/{self.repo}/installation",
                    accept="application/vnd.github+json",
                    jwt=await get_jwt(),
                )

                self.id = result["id"]

        return self.id


_id_store = IDStore()


async def get_installation_id():
    """Get an installation ID that has access to the given repo url."""
    return await _id_store.get_id()
