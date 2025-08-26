import logging
from typing import Any

from gidgethub import routing, sansio
from repligit.asyncio import fetch_pack, ls_remote, send_pack

from hubcast.web.utils import get_repo_config


class GitHubRouter(routing.Router):
    """
    Custom router to handle GitHub interactions for hubcast
    """

    async def dispatch(self, event: sansio.Event, *args: Any, **kwargs: Any) -> None:
        """Dispatch an event to all registered function(s)."""
        found_callbacks = self.fetch(event)
        for callback in found_callbacks:
            await callback(event, *args, **kwargs)


router = GitHubRouter()
log = logging.getLogger(__name__)


# -----------------------------------
# Push Events
# -----------------------------------
@router.register("push", deleted=False)
async def sync_branch(event, gh, gl, gl_user, *args, **kwargs):
    """Sync the git branch referenced to GitLab."""
    src_repo_url = event.data["repository"]["clone_url"]
    src_fullname = event.data["repository"]["full_name"]
    src_owner, src_repo_name = src_fullname.split("/")
    want_sha = event.data["head_commit"]["id"]
    target_ref = event.data["ref"]

    # skip branches from push events that are also pull requests
    if await gh.get_prs(branch=target_ref):
        return

    repo_config = await get_repo_config(gh, src_fullname, refresh=True)

    dest_fullname = f"{repo_config.dest_org}/{repo_config.dest_name}"
    dest_remote_url = f"{gl.instance_url}/{dest_fullname}.git"

    # setup callback webhook on GitLab
    webhook_data = {
        "src_owner": src_owner,
        "src_repo_name": src_repo_name,
        "src_check_name": repo_config.check_name,
        "src_forge": "github",
    }
    await gl.set_webhook(dest_fullname, webhook_data)

    # sync commits from GitHub -> GitLab
    gl_refs = await ls_remote(dest_remote_url)
    have_shas = gl_refs.values()
    from_sha = gl_refs.get(target_ref) or ("0" * 40)

    if want_sha in have_shas:
        log.info(f"[{src_fullname}]: {target_ref} already up-to-date")
        return

    packfile = await fetch_pack(
        src_repo_url,
        want_sha,
        have_shas,
    )

    gl_token = await gl.auth.authenticate_installation(gl_user)

    log.info(f"[{src_fullname}]: mirroring {from_sha} -> {want_sha}")
    await send_pack(
        dest_remote_url,
        target_ref,
        from_sha,
        want_sha,
        packfile,
        username=gl_user,
        password=gl_token,
    )


@router.register("push", deleted=True)
async def remove_branch(event, gh, gl, gl_user, *args, **kwargs):
    src_fullname = event.data["repository"]["full_name"]
    target_ref = event.data["ref"]

    repo_config = await get_repo_config(gh, src_fullname, refresh=True)

    dest_fullname = f"{repo_config.dest_org}/{repo_config.dest_name}"
    dest_remote_url = f"{gl.instance_url}/{dest_fullname}.git"

    gl_refs = await ls_remote(dest_remote_url)
    head_sha = gl_refs.get(target_ref)
    null_sha = "0" * 40

    gl_token = await gl.auth.authenticate_installation(gl_user)

    log.info(f"[{src_fullname}]: deleting {target_ref}")
    await send_pack(
        dest_remote_url,
        target_ref,
        head_sha,
        null_sha,
        b"",
        username=gl_user,
        password=gl_token,
    )


# -----------------------------------
# Pull Request Events
# -----------------------------------
@router.register("pull_request", action="opened")
@router.register("pull_request", action="reopened")
@router.register("pull_request", action="synchronize")
async def sync_pr(event, gh, gl, gl_user, *args, **kwargs):
    """Sync the git fork/branch referenced in a PR to GitLab."""
    pull_request = event.data["pull_request"]
    pull_request_id = pull_request["number"]

    src_repo_url = pull_request["head"]["repo"]["clone_url"]
    src_fullname = pull_request["head"]["repo"]["full_name"]
    want_sha = pull_request["head"]["sha"]

    # pull requests coming from forks are pushed as branches in the form of
    # pr-<pr-number> instead of as their branch name as conflicts could occur
    # between multiple repositories
    is_pull_request_fork = src_fullname != pull_request["base"]["repo"]["full_name"]
    if is_pull_request_fork:
        target_ref = f"refs/heads/pr-{pull_request_id}"
    else:
        target_ref = f"refs/heads/{pull_request['head']['ref']}"

    # get the repository configuration
    repo_config = await get_repo_config(gh, src_fullname)

    dest_fullname = f"{repo_config.dest_org}/{repo_config.dest_name}"
    dest_remote_url = f"{gl.instance_url}/{dest_fullname}.git"

    gl_refs = await ls_remote(dest_remote_url)
    have_shas = gl_refs.values()
    from_sha = gl_refs.get(target_ref) or ("0" * 40)

    if want_sha in have_shas:
        log.info(f"[{src_fullname}]: {target_ref} already up-to-date")
        return

    # fetch differential packfile with all new commits
    packfile = await fetch_pack(
        src_repo_url,
        want_sha,
        have_shas,
    )

    gl_token = await gl.auth.authenticate_installation(gl_user)

    # upload packfile to gitlab repository
    log.info(f"[{src_fullname}]: mirroring {from_sha} -> {want_sha}")
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
async def remove_pr(event, gh, gl, gl_user, *args, **kwargs):
    pull_request = event.data["pull_request"]
    src_fullname = pull_request["head"]["repo"]["full_name"]

    # if the pull request comes from a fork we should clean up
    # the branch upon closing or merging the PR. However, if the
    # pull request comes from an internal branch we should wait
    # to clean up the branch when the branch is deleted from the
    # internal repository
    is_pull_request_fork = src_fullname != pull_request["base"]["repo"]["full_name"]
    if not is_pull_request_fork:
        return

    pull_request_id = pull_request["number"]
    target_ref = f"refs/heads/pr-{pull_request_id}"

    # get the repository configuration
    repo_config = await get_repo_config(gh, src_fullname)

    dest_fullname = f"{repo_config.dest_org}/{repo_config.dest_name}"
    dest_remote_url = f"{gl.instance_url}/{dest_fullname}.git"

    gl_refs = await ls_remote(dest_remote_url)
    head_sha = gl_refs.get(target_ref)
    null_sha = "0" * 40

    gl_token = await gl.auth.authenticate_installation(gl_user)

    log.info(f"[{src_fullname}]: deleting {target_ref}")
    await send_pack(
        dest_remote_url,
        target_ref,
        head_sha,
        null_sha,
        b"",
        username=gl_user,
        password=gl_token,
    )
