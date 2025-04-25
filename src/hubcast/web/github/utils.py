from hubcast.clients.github import GitHubClient
from hubcast.repos.config import ConfigCache, create_config

config_cache = ConfigCache()


async def get_repo_config(gh: GitHubClient, fullname: str):
    if fullname in config_cache:
        config = config_cache[fullname]
    else:
        data = await gh.get_repo_config(fullname)
        config = create_config(data)
        config_cache[fullname] = config

    return config
