import pytest
from configparser import ConfigParser
from shutil import which
from hubcast.utils.git import Git

if not which("git"):
    pytest.skip(
        "Skipping git tests since git command not found", allow_module_level=True
    )


@pytest.fixture
def remote_name():
    return "github"


@pytest.fixture
def remote_url():
    return "https://github.com/LLNL/hubcast.git"


@pytest.fixture
def repo_path(tmp_path):
    return str(tmp_path)


@pytest.fixture
def git(repo_path):
    return Git(config={"repo_path": repo_path})


def test_basic_repo_operations(git, repo_path, remote_name, remote_url):
    # Setup
    config = ConfigParser()
    config_path = f"{repo_path}/.git/config"

    # Execute
    git("init")
    git(f"remote add {remote_name} {remote_url}")

    # Verify
    config.read(config_path)
    actual_remote_key = next((key for key in config.keys() if remote_name in key), None)
    actual_url = config[actual_remote_key]["url"]
    assert actual_url == remote_url
