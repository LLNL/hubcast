import logging
from typing import Any

from gidgetlab import routing, sansio
from repligit.asyncio import fetch_pack, ls_remote, send_pack

from hubcast.web.utils import get_repo_config


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
            await callback(event, *args, **kwargs)


router = GitLabRouter()
log = logging.getLogger(__name__)


# -----------------------------------
# Push Events
# -----------------------------------
@router.register("Push Hook")
async def sync_branch(event, gl_src, gl_dest, dest_user, *args, **kwargs):
    """Sync a git branch to the destination."""

    # manually handle deleted branches unlike github, which provides the `deleted` attribute
    if event.data["after"] == "0" * 40:
        await remove_branch(event, gl_src, gl_dest, dest_user, *args, **kwargs)
        return

    src_repo_url = event.data["repository"]["git_http_url"]
    src_fullname = event.data["project"]["path_with_namespace"]
    repo_id = event.data["project_id"]
    # after represents the new HEAD of the ref
    want_sha = event.data["after"]
    target_ref = event.data["ref"]

    # skip branches from push events that are also merge requests
    src_refs = await ls_remote(src_repo_url)
    pull_refs = [
        src_refs[ref] for ref in src_refs if ref.startswith("refs/merge-requests/")
    ]
    if want_sha in pull_refs:
        return

    repo_config = await get_repo_config(gl_src, src_fullname, refresh=True)

    dest_fullname = f"{repo_config.dest_org}/{repo_config.dest_name}"
    dest_remote_url = f"{gl_dest.instance_url}/{dest_fullname}.git"

    webhook_data = {
        "src_repo_id": repo_id,
        "src_check_name": repo_config.check_name,
        "src_service": "gitlab",
    }
    await gl_dest.set_webhook(dest_fullname, webhook_data)

    # sync commits from source -> destination
    dest_refs = await ls_remote(dest_remote_url)
    have_shas = dest_refs.values()
    from_sha = dest_refs.get(target_ref) or ("0" * 40)

    if want_sha in have_shas:
        log.info(f"[{src_fullname}]: {target_ref} already up-to-date")
        return

    packfile = await fetch_pack(src_repo_url, want_sha, have_shas)

    dest_token = await gl_dest.auth.authenticate_installation(dest_user)

    log.info(f"[{src_fullname}]: mirroring {from_sha} -> {want_sha}")
    await send_pack(
        dest_remote_url,
        target_ref,
        from_sha,
        want_sha,
        packfile,
        username=dest_user,
        password=dest_token,
    )


async def remove_branch(event, gl_src, gl_dest, dest_user, *args, **kwargs):
    """Delete a git branch from a destination."""

    src_fullname = event.data["project"]["path_with_namespace"]
    target_ref = event.data["ref"]

    repo_config = await get_repo_config(gl_src, src_fullname, refresh=True)

    dest_fullname = f"{repo_config.dest_org}/{repo_config.dest_name}"
    dest_remote_url = f"{gl_dest.instance_url}/{dest_fullname}.git"

    dest_refs = await ls_remote(dest_remote_url)
    head_sha = dest_refs.get(target_ref)
    null_sha = "0" * 40

    dest_token = await gl_dest.auth.authenticate_installation(dest_user)

    log.info(f"[{src_fullname}]: deleting {target_ref}")
    await send_pack(
        dest_remote_url,
        target_ref,
        head_sha,
        null_sha,
        b"",
        username=dest_user,
        password=dest_token,
    )


# -----------------------------------
# Merge Request Events
# -----------------------------------
@router.register("Merge Request Hook", action="open")
@router.register("Merge Request Hook", action="reopen")
@router.register("Merge Request Hook", action="update")
async def sync_mr(event, gl_src, gl_dest, dest_user, *args, **kwawrgs):
    """Sync the git fork/branch referenced in an MR to the destination."""

    merge_request_id = event.data["object_attributes"]["iid"]

    src_repo_url = event.data["object_attributes"]["source"]["git_http_url"]
    src_fullname = event.data["object_attributes"]["source"]["path_with_namespace"]
    want_sha = event.data["object_attributes"]["last_commit"]["id"]

    # merge requests coming from forks are pushed as branches in the form of
    # mr-<mr-number> instead of as their branch name as conflicts could occur
    # between multiple repositories
    is_from_fork = (
        event.data["object_attributes"]["source"]["id"]
        != event.data["object_attributes"]["target"]["id"]
    )
    if is_from_fork:
        target_ref = f"refs/heads/mr-{merge_request_id}"
    else:
        target_ref = f"refs/heads/{event.data['object_attributes']['source_branch']}"

    repo_config = await get_repo_config(gl_src, src_fullname, refresh=True)

    dest_fullname = f"{repo_config.dest_org}/{repo_config.dest_name}"
    dest_remote_url = f"{gl_dest.instance_url}/{dest_fullname}.git"

    # sync commits from source -> destination
    dest_refs = await ls_remote(dest_remote_url)
    have_shas = dest_refs.values()
    from_sha = dest_refs.get(target_ref) or ("0" * 40)

    if want_sha in have_shas:
        log.info(f"[{src_fullname}]: {target_ref} already up-to-date")
        return

    packfile = await fetch_pack(src_repo_url, want_sha, have_shas)

    dest_token = await gl_dest.auth.authenticate_installation(dest_user)

    log.info(f"[{src_fullname}]: mirroring {from_sha} -> {want_sha}")
    await send_pack(
        dest_remote_url,
        target_ref,
        from_sha,
        want_sha,
        packfile,
        username=dest_user,
        password=dest_token,
    )


@router.register("Merge Request Hook", action="close")
async def remove_mr(event, gl_src, gl_dest, dest_user, *args, **kwawrgs):
    src_fullname = event.data["object_attributes"]["source"]["path_with_namespace"]

    # if the merge request comes from a fork we should clean up
    # the branch upon closing or merging the MR. However, if the
    # merge request comes from an internal branch we should wait
    # to clean up the branch when the branch is deleted from the
    # internal repository
    is_from_fork = (
        event.data["object_attributes"]["source"]["id"]
        != event.data["object_attributes"]["target"]["id"]
    )
    if not is_from_fork:
        return

    merge_request_id = event.data["object_attributes"]["iid"]
    target_ref = f"refs/heads/mr-{merge_request_id}"

    repo_config = await get_repo_config(gl_src, src_fullname, refresh=True)

    dest_fullname = f"{repo_config.dest_org}/{repo_config.dest_name}"
    dest_remote_url = f"{gl_dest.instance_url}/{dest_fullname}.git"

    dest_refs = await ls_remote(dest_remote_url)
    head_sha = dest_refs.get(target_ref)
    null_sha = "0" * 40

    dest_token = await gl_dest.auth.authenticate_installation(dest_user)

    log.info(f"[{src_fullname}]: deleting {target_ref}")
    await send_pack(
        dest_remote_url,
        target_ref,
        head_sha,
        null_sha,
        b"",
        username=dest_user,
        password=dest_token,
    )


@router.register("Pipeline Hook", status="pending")
@router.register("Pipeline Hook", status="running")
@router.register("Pipeline Hook", status="success")
@router.register("Pipeline Hook", status="failed")
@router.register("Pipeline Hook", status="canceled")
async def status_relay(
    event, src_service: str, src_client, src_check_name, *arg, **kwargs
):
    """Relay status of a GitLab pipeline back to GitHub."""
    # get ref from event
    ref = event.data["object_attributes"]["sha"]

    # get status from event
    ci_status = event.data["object_attributes"]["status"]
    pipeline_url = event.data["object_attributes"]["url"]

    if src_service == "gitlab":
        # doesn't need to be mapped
        status = ci_status
    elif src_service == "github":
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

    # both gitlab and github src clients have the same signature
    await src_client.set_check_status(ref, src_check_name, status, pipeline_url)
