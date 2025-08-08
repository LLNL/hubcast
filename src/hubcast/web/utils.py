from typing import Dict

from hubcast.clients.github import GitHubClient
from hubcast.clients.gitlab import GitLabSrcClient
from hubcast.repos.config import RepoConfig

config_cache = dict()


def create_config(fullname: str, data: Dict) -> RepoConfig:
    return RepoConfig(
        fullname=fullname,
        dest_org=data["Repo"]["owner"],
        dest_name=data["Repo"]["name"],
    )


async def get_repo_config(
    src_client: GitHubClient | GitLabSrcClient, fullname: str, refresh: bool = False
):
    # the client must implement the get_repo_config method in the standard format
    if fullname in config_cache and not refresh:
        config = config_cache[fullname]
    else:
        data = await src_client.get_repo_config()
        config = create_config(fullname, data)
        config_cache[fullname] = config

    return config
