import logging

import aiohttp
import yaml
from gidgethub import aiohttp as gh_aiohttp

from .auth import GitHubAuthenticator

log = logging.getLogger(__name__)


class InvalidConfigYAMLError(Exception):
    pass


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

    async def set_check_status(
        self, ref: str, check_name: str, status: str, details_url: str
    ):
        # construct upload payload
        payload = {"name": check_name, "head_sha": ref, "details_url": details_url}

        # for success and failure status write out a conclusion
        if status in ("success", "failure", "cancelled"):
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
            url = f"/repos/{self.repo_owner}/{self.repo_name}/commits/{ref}/check-runs"
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
                url = f"/repos/{self.repo_owner}/{self.repo_name}/check-runs"
                await gh.post(url, data=payload)
            else:
                url = f"/repos/{self.repo_owner}/{self.repo_name}/check-runs/{existing_check['id']}"
                await gh.patch(url, data=payload)

    async def get_repo_config(self):
        gh_token = await self.auth.authenticate_installation(
            self.repo_owner, self.repo_name
        )

        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(session, self.requester, oauth_token=gh_token)

            # get the contents of the repository hubcast.yml file
            # the forge is github so the config will be under .github
            url = f"/repos/{self.repo_owner}/{self.repo_name}/contents/.github/hubcast.yml"
            # get raw contents rather than base64 encoded text
            config_str = await gh.getitem(url, accept="application/vnd.github.raw")

            try:
                config = yaml.safe_load(config_str)
            except yaml.YAMLError as exc:
                log.error(
                    f"[{self.repo_owner}/{self.repo_name}]: Unable to parse config: {exc}"
                )
                raise InvalidConfigYAMLError()

            return config

    async def get_prs(self, branch=None):
        """Returns a list of all open PR numbers; can be filtered by internal branches."""

        gh_token = await self.auth.authenticate_installation(
            self.repo_owner, self.repo_name
        )

        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(session, self.requester, oauth_token=gh_token)

            # https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests
            # default is open pull requests
            url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls"
            if branch:
                # head: filter pulls by head user or head organization and branch name
                url = f"{url}?head={self.repo_owner}:{branch}"
                prs_res = await gh.getitem(url)
                return [pr["number"] for pr in prs_res]
