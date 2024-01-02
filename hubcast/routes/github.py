import asyncio
from typing import Any

from gidgethub import routing, sansio

from ..models import HubcastRepo
from ..utils.git import Git


class LabSyncRouter(routing.Router):

    """
    Custom router to handle common interactions for labsync
    """

    async def dispatch(self, event: sansio.Event, *args: Any, **kwargs: Any) -> None:
        """Dispatch an event to all registered function(s)."""

        found_callbacks = self.fetch(event)
        for callback in found_callbacks:
            await callback(event, *args, **kwargs)


router = LabSyncRouter()
repo_lock = asyncio.Lock()


@router.register("pull_request", action="opened")
@router.register("pull_request", action="reopened")
@router.register("pull_request", action="synchronize")
async def sync_pr(event, repo: HubcastRepo, gh, *arg, **kwargs):
    """Sync the git fork/branch referenced in a PR to GitLab."""
    git = Git(config=repo.git_repo_path)
    pull_request = event.data["pull_request"]
    pull_request_id = pull_request["number"]
    await repo_lock.acquire()
    try:
        git(f"fetch github pull/{pull_request_id}/head")
        git(f"push gitlab FETCH_HEAD:refs/heads/pr-{pull_request_id}")
    finally:
        repo_lock.release()


@router.register("pull_request", action="closed")
async def remove_pr(event, repo: HubcastRepo, gh, *arg, **kwargs):
    git = Git(config=repo.git_repo_path)
    pull_request = event.data["pull_request"]
    pull_request_id = pull_request["number"]
    await repo_lock.acquire()
    try:
        git(f"push -d gitlab refs/heads/pr-{pull_request_id}")
    finally:
        repo_lock.release()
