import subprocess

from collections import defaultdict
from typing import Dict, List
from dataclasses import dataclass, field


# https://git-scm.com/docs/gitcredentials#_custom_helpers
def credential_helper(remote: str, url: str) -> str:
    remote = remote.upper()
    config_key = f"credential.{url}.helper"
    helper_func = f"""!f() {{ echo "username=${remote}_USERNAME"; echo "password=${remote}_TOKEN"; }};f"""
    return f"""{config_key}={helper_func}"""


@dataclass
class Git:
    env: Dict[str, str] = field(default_factory=lambda: defaultdict(Dict[str, str]))
    flags: List[str] = field(default_factory=lambda: defaultdict(List[str]))

    def __call__(self, args: List[str]):
        """Executes a git command on the host system."""
        result = subprocess.run(
            ["git", *self.flags, *args],
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
