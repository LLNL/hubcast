import logging
from typing import Dict

from hubcast.clients.github import GitHubClient
from hubcast.repos.config import RepoConfig
from src.hubcast.clients.github.client import InvalidConfigYAMLError

config_cache = dict()
log = logging.getLogger(__name__)


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
        try:
            data = await gh.get_repo_config()
        except InvalidConfigYAMLError:
            log.exception("Repo config parse failed")

        config = create_config(fullname, data)
        config_cache[fullname] = config

    return config
