import os
import shlex
import subprocess
from attrs import define, field


@define
class Git:
    config: dict = field()
    repo_path: str = field()

    @config.default
    def _config(self) -> dict:
        return {}

    @repo_path.default
    def _repo_path(self) -> str:
        return self.config.get("repo_path", os.getcwd())

    def __call__(self, args: str) -> subprocess.CompletedProcess:
        """Executes a git command on the host system."""
        result = subprocess.run(
            ["git", "-C", f"{self.repo_path}"] + shlex.split(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
        )
        return result
