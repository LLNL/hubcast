import os
import shlex
import subprocess
from attrs import define, field


@define
class Git:
    config: dict = field(factory=dict)
    base_path: str = field()

    @base_path.default
    def _base_path(self) -> str:
        return self.config.get("base_path", os.getcwd())

    def __call__(self, args: str) -> subprocess.CompletedProcess:
        """Executes a git command on the host system."""
        result = subprocess.run(
            ["git", "-C", f"{self.base_path}"] + shlex.split(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
        )
        return result
