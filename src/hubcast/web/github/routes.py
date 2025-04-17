import logging
from typing import Any

from gidgethub import routing, sansio
from repligit.asyncio import fetch_pack, ls_remote, send_pack

log = logging.getLogger(__name__)


class GitHubRouter(routing.Router):
    """
    Custom router to handle common interactions for labsync
    """

    async def dispatch(self, event: sansio.Event, *args: Any, **kwargs: Any) -> None:
        """Dispatch an event to all registered function(s)."""
        found_callbacks = self.fetch(event)
        for callback in found_callbacks:
            await callback(event, *args, **kwargs)


router = GitHubRouter()


@router.register("pull_request", action="opened")
@router.register("pull_request", action="reopened")
@router.register("pull_request", action="synchronize")
async def sync_pr(event, gh, gl, gl_user, *arg, **kwargs):
    """Sync the git fork/branch referenced in a PR to GitLab."""
    pull_request = event.data["pull_request"]

    pull_request_id = pull_request["number"]
    repo_url = pull_request["head"]["repo"]["clone_url"]
    full_name = pull_request["head"]["repo"]["full_name"]
    want_sha = pull_request["head"]["sha"]

    target_ref = f"refs/heads/pr-{pull_request_id}"
    dest_remote_url = f"{gl.instance_url}/{full_name}.git"

    gl_refs = await ls_remote(dest_remote_url)

    have_shas = gl_refs.values()

    from_sha = gl_refs.get(target_ref) or ("0" * 40)

    if want_sha in have_shas:
        log.info(f"[{full_name}]: PR #{pull_request_id} already up-to-date")
        return

    packfile = await fetch_pack(
        repo_url,
        want_sha,
        have_shas,
    )

    gl_token = await gl.auth.authenticate_installation(gl_user)

    log.info(f"[{full_name}]: mirroring {from_sha} -> {want_sha}")
    await send_pack(
        dest_remote_url,
        target_ref,
        from_sha,
        want_sha,
        packfile,
        username=gl_user,
        password=gl_token,
    )


@router.register("pull_request", action="closed")
async def remove_pr(event, gh, gl, gl_user, *arg, **kwargs):
    pull_request = event.data["pull_request"]
    pull_request_id = pull_request["number"]
    full_name = pull_request["head"]["repo"]["full_name"]

    dest_remote_url = f"{gl.instance_url}/{full_name}.git"
    target_ref = f"refs/heads/pr-{pull_request_id}"

    gl_refs = await ls_remote(dest_remote_url)

    head_sha = gl_refs.get(target_ref)
    null_sha = "0" * 40

    gl_token = await gl.auth.authenticate_installation(gl_user)

    log.info(f"[{full_name}]: deleting {target_ref}")
    await send_pack(
        dest_remote_url,
        target_ref,
        head_sha,
        null_sha,
        b"",
        username=gl_user,
        password=gl_token,
    )
