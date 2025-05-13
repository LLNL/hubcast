from hubcast.clients.github import GitHubClient
from hubcast.repos.config import RepoConfig

from typing import Dict

config_cache = dict()


def create_config(fullname: str, data: Dict) -> RepoConfig:
    return RepoConfig(
        fullname=fullname,
        dest_org=data["Repo"]["owner"],
        dest_name=data["Repo"]["name"],
    )


async def get_repo_config(gh: GitHubClient, fullname: str, refresh: bool = False):
    if fullname in config_cache and not refresh:
        config = config_cache[fullname]
    else:
        data = await gh.get_repo_config()
        config = create_config(fullname, data)
        config_cache[fullname] = config

    return config
