from typing import Any

from gidgetlab import routing, sansio
from gidgethub import aiohttp as gh_aiohttp
from gidgetlab import aiohttp as gl_aiohttp

from ..models import HubcastRepo


class HubCastRouter(routing.Router):

    """
    Custom router to handle common interactions for hubcast
    """

    async def dispatch(
        self, event: sansio.Event, repo: HubcastRepo, *args: Any, **kwargs: Any
    ) -> None:
        """Dispatch an event to all registered function(s)."""

        found_callbacks = []
        try:
            found_callbacks.extend(self._shallow_routes[event.event])
        except KeyError:
            pass
        try:
            details = self._deep_routes[event.event]
        except KeyError:
            pass
        else:
            for data_key, data_values in details.items():
                if data_key in event.object_attributes:
                    event_value = event.object_attributes[data_key]
                    if event_value in data_values:
                        found_callbacks.extend(data_values[event_value])
        for callback in found_callbacks:
            await callback(event, *args, **kwargs)


router = HubCastRouter()


@router.register("Pipeline Hook", status="pending")
@router.register("Pipeline Hook", status="running")
@router.register("Pipeline Hook", status="success")
@router.register("Pipeline Hook", status="failure")
async def opened_issue(
    event: sansio.Event,
    repo: HubcastRepo,
    gh: gh_aiohttp.GitHubAPI,
    gl: gl_aiohttp.GitLabAPI,
    *arg,
    **kwargs,
):
    """Relay status of a GitLab pipeline back to GitHub."""
    owner = repo.github_config.owner
    repo_name = repo.github_config.repo

    # get ref from event
    ref = event.data["object_attributes"]["sha"]

    # get status from event
    ci_status = event.data["object_attributes"]["status"]

    # construct upload payload
    payload = {
        "name": repo.github_config.check_name,
        "head_sha": ref,
    }

    if ci_status == "pending":
        payload["status"] = "queued"
    elif ci_status == "running":
        payload["status"] = "in_progress"
    elif ci_status == "success":
        payload["status"] = "completed"
        payload["conclusion"] = "success"
    else:
        payload["status"] = "completed"
        payload["conclusion"] = "failure"

    # get a list of the checks on a commit
    url = f"/repos/{owner}/{repo_name}/commits/{ref}/check-runs"
    data = await gh.getitem(url)

    # search for existing check with GH_CHECK_NAME
    existing_check = None
    for check in data["check_runs"]:
        if check["name"] == repo.github_config.check_name:
            existing_check = check
            break

    # create a new check if no previous check is found, or if the previous
    # existing check was marked as completed. (This allows to check re-runs.)
    if existing_check is None or existing_check["status"] == "completed":
        url = f"/repos/{owner}/{repo_name}/check-runs"
        await gh.post(url, data=payload)
    else:
        url = f"/repos/{owner}/{repo_name}/check-runs/{existing_check['id']}"
        await gh.patch(url, data=payload)
