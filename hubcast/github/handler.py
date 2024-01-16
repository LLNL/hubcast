import asyncio
import os
import sys
import traceback
from subprocess import CalledProcessError
from typing import Dict

import aiohttp
from aiohttp import web
from gidgethub import aiohttp as gh_aiohttp
from gidgethub import sansio
from gidgetlab import aiohttp as gl_aiohttp

from hubcast.account_map.abc import AccountMap
from hubcast.github import config
from hubcast.github.auth import GitHubAuthenticator
from hubcast.github.routes import router
from hubcast.gitlab.auth import GitLabAuthenticator
from hubcast.utils.git import Git


async def create_repo(
    git: Git,
    repo_lock: asyncio.Lock,
    repo_path: str,
    github_url: str,
    gitlab_url: str,
):
    await repo_lock.acquire()
    try:
        if not os.path.exists(repo_path):
            os.makedirs(repo_path)
            git("init")
            git(f"remote add github {github_url}")
            git(f"remote add gitlab {gitlab_url}")

    except CalledProcessError:
        os.rmdir(repo_path)

    finally:
        repo_lock.release()


class GitHubHandler:
    def __init__(
        self,
        gh_authenticator: GitHubAuthenticator,
        gh_requester: str,
        webhook_secret: str,
        repos_path: str,
        account_map: AccountMap,
        gl_authenticator: GitLabAuthenticator,
        gl_instance_url: str,
    ):
        self.auth = gh_authenticator
        self.requester = gh_requester
        self.webhook_secret = webhook_secret
        self.repos_path = repos_path
        self.account_map = account_map
        self.gl_auth = gl_authenticator
        self.gl_instance_url = gl_instance_url
        self.repo_locks: Dict[str, asyncio.Lock] = {}

    async def handle(self, request):
        try:
            # read the GitHub webhook payload
            body = await request.read()
            event = sansio.Event.from_http(
                request.headers, body, secret=self.webhook_secret
            )
            print("GH delivery ID", event.delivery_id, file=sys.stderr)

            # get the owner and name of the repo which sent the event
            repo_data = event.data["repository"]
            [repo_owner, repo_name] = repo_data["full_name"].split("/", 1)
            repo_path = f"{self.repos_path}/{repo_owner}/{repo_name}"

            # create a repo lock if it doesn't already exist
            if repo_path not in self.repo_locks:
                self.repo_locks[repo_path] = asyncio.Lock()

            repo_lock = self.repo_locks[repo_path]

            # put account map conversation here
            try:
                github_user = event.data["sender"]["login"]
                gitlab_user = self.account_map(github_user)
            except Exception as exc:
                print(exc)
                return web.Response(status=200)

            if gitlab_user is None:
                print("Unauthorized User")
                return web.Response(status=200)

            # get limited scope tokens for github and gitlab clients
            github_token = await self.auth.authenticate_installation(
                repo_owner, repo_name
            )
            gitlab_token = await self.gl_auth.authenticate_installation(gitlab_user)

            # create git object for callback functions
            git = Git(
                repo_path,
                gh_username=self.requester,
                gh_token=github_token,
                gl_username=gitlab_user,
                gl_token=gitlab_token,
                gl_instance_url=self.gl_instance_url,
            )

            async with aiohttp.ClientSession() as session:
                gh = gh_aiohttp.GitHubAPI(
                    session, self.requester, oauth_token=github_token
                )
                gl = gl_aiohttp.GitLabAPI(
                    session,
                    gitlab_user,
                    url=self.gl_instance_url,
                    access_token=gitlab_token,
                )

                # create local git repository if it doesn't already exist
                if not os.path.exists(repo_path):
                    gl_owner, gl_name = await config.gitlab_owner_name(
                        gh, repo_owner, repo_name
                    )

                    github_url = f"https://github.com/{repo_owner}/{repo_name}.git"
                    gitlab_url = f"{self.gl_instance_url}/{gl_owner}/{gl_name}.git"

                    await create_repo(git, repo_lock, repo_path, github_url, gitlab_url)

                # call the appropriate callback for the event
                await router.dispatch(event, gh, gl, git, repo_lock, session=session)

                # return a "Success"
                return web.Response(status=200)

        except Exception:
            traceback.print_exc(file=sys.stderr)
            return web.Response(status=500)
