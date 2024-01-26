import base64

import yaml
from gidgethub import aiohttp as gh_aiohttp


async def gitlab_owner_name(gh: gh_aiohttp.GitHubAPI, gh_owner, gh_name):
    url = f"/repos/{gh_owner}/{gh_name}/contents/.github/hubcast.yml"
    result = await gh.getitem(url, accept="application/vnd.github+json")

    config_data = base64.b64decode(result["content"])
    config = yaml.safe_load(config_data)

    gl_owner = config["Repo"]["owner"]
    gl_name = config["Repo"]["name"]

    return (gl_owner, gl_name)
