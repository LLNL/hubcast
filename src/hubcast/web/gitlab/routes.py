import logging
from typing import Any

from gidgetlab import routing, sansio

log = logging.getLogger(__name__)


class GitLabRouter(routing.Router):
    """
    Custom router to handle common interactions for hubcast
    """

    async def dispatch(self, event: sansio.Event, *args: Any, **kwargs: Any) -> None:
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
            try:
                await callback(event, *args, **kwargs)
            except Exception:
                # this catches errors related to processing of webhook events
                log.exception(
                    "Failed to process GitLab webhook event",
                    extra={
                        "event_type": event.event,
                    },
                )


router = GitLabRouter()


@router.register("Pipeline Hook", status="pending")
@router.register("Pipeline Hook", status="running")
@router.register("Pipeline Hook", status="success")
@router.register("Pipeline Hook", status="failed")
@router.register("Pipeline Hook", status="canceled")
async def status_relay(event, gh, gh_check_name, *arg, **kwargs):
    """Relay status of a GitLab pipeline back to GitHub."""
    # get ref from event
    ref = event.data["object_attributes"]["sha"]

    # get status from event
    ci_status = event.data["object_attributes"]["status"]
    pipeline_url = event.data["object_attributes"]["url"]

    # https://docs.github.com/en/rest/guides/using-the-rest-api-to-interact-with-checks#about-check-suites
    # https://docs.gitlab.com/api/pipelines/#list-project-pipelines -> status description

    # translate between GitLab and GitHub statuses
    if ci_status == "pending":
        status = "queued"
    elif ci_status == "running":
        status = "in_progress"
    elif ci_status == "failed":
        status = "failure"
    elif ci_status == "canceled":
        status = "cancelled"
    else:
        status = ci_status

    await gh.set_check_status(ref, gh_check_name, status, pipeline_url)
