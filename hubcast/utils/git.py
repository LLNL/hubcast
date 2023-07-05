import os
import subprocess

# get configuration from environment.
GIT_REPO_PATH = os.environ.get("HC_GIT_REPO_PATH")


def git(args):
    """Executes a git command on the host system."""
    result = subprocess.run(
        ["git", "-C", f"{GIT_REPO_PATH}"] + args.split(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
    )
    return result
