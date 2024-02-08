import shlex
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List


# https://git-scm.com/docs/gitcredentials#_custom_helpers
def credential_helper(remote: str, url: str) -> str:
    remote = remote.upper()

    username_str = f"username=${remote}_USERNAME"
    pass_str = f"password=${remote}_TOKEN"

    helper_func = f"""!f() {{ echo "{username_str}"; echo "{pass_str}"; }};f"""
    return f"""credential.{url}.helper={helper_func}"""


@dataclass
class Git:
    env: Dict[str, str] = field(default_factory=lambda: {})
    flags: List[str] = field(default_factory=lambda: [])

    def __call__(self, args: str):
        """Executes a git command on the host system."""
        return subprocess.run(
            ["git", *self.flags] + shlex.split(args),
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
