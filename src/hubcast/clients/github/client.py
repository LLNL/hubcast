import aiohttp
from gidgethub import aiohttp as gh_aiohttp

from .auth import GitHubAuthenticator


class GitHubClientFactory:
    def __init__(self, app_id, privkey, requester):
        self.requester = requester
        self.auth = GitHubAuthenticator(requester, privkey, app_id)

    def create_client(self, repo_owner, repo_name):
        return GitHubClient(self.auth, self.requester, repo_owner, repo_name)


class GitHubClient:
    def __init__(self, auth, requester, repo_owner, repo_name):
        self.auth = auth
        self.requester = requester
        self.repo_owner = repo_owner
        self.repo_name = repo_name

    async def getitem(self, url):
        gh_token = await self.auth.authenticate_installation(
            self.repo_owner, self.repo_name
        )

        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(session, self.requester, oauth_token=gh_token)
            return await gh.getitem(url)

    async def post(self, url, data=None):
        gh_token = await self.auth.authenticate_installation(
            self.repo_owner, self.repo_name
        )

        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(session, self.requester, oauth_token=gh_token)
            return await gh.post(url, data=data)

    async def patch(self, url, data=None):
        gh_token = await self.auth.authenticate_installation(
            self.repo_owner, self.repo_name
        )

        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(session, self.requester, oauth_token=gh_token)
            return await gh.patch(url, data=data)
