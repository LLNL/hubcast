import time
from typing import Awaitable, Callable, Tuple


class TokenCache:
    """
    Cache for web tokens with an expiration.
    """

    def __init__(self) -> None:
        self._tokens = {}

    async def get(
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
        renew: Callable[[], Awaitable[Tuple[float, str]]]
            A function to call in order to generate a new token if the cache
            is stale.
        time_needed: int
            The number of seconds a token will be needed. Thus any token that
            expires during this window should be disregarded and renewed.
        """
        expires, token = self._tokens.get(name, (0, ""))

        now = time.time()
        if expires < now + time_needed:
            expires, token = await renew()
            self._tokens[name] = (expires, token)

        return token
