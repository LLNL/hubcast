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

    async def set_check_status(self, ref: str, check_name: str, status: str):
        # construct upload payload
        payload = {
            "name": check_name,
            "head_sha": ref,
        }

        # for sucess and failure status write out a conclusion
        if status in ("sucess", "failure"):
            payload["status"] = "completed"
            payload["conclusion"] = status
        else:
            payload["status"] = status

        gh_token = await self.auth.authenticate_installation(
            self.repo_owner, self.repo_name
        )

        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(session, self.requester, oauth_token=gh_token)

            # get a list of the checks on a commit
            url = f"/repos/{gh.repo_owner}/{gh.repo_name}/commits/{ref}/check-runs"
            data = await gh.getitem(url)

            # search for existing check with GH_CHECK_NAME
            existing_check = None
            for check in data["check_runs"]:
                if check["name"] == check_name:
                    existing_check = check
                    break

            # create a new check if no previous check is found, or if the previous
            # existing check was marked as completed. (This allows to check re-runs.)
            if existing_check is None or existing_check["status"] == "completed":
                url = f"/repos/{gh.repo_owner}/{gh.repo_name}/check-runs"
                await gh.post(url, data=payload)
            else:
                url = f"/repos/{gh.repo_owner}/{gh.repo_name}/check-runs/{existing_check['id']}"
                await gh.patch(url, data=payload)
