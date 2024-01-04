import pytest

from hubcast.models import HubcastRepo


@pytest.fixture
def owner():
    return "LLNL"


@pytest.fixture
def repo():
    return "hubcast"


@pytest.fixture
def url(owner, repo):
    return f"git@github.com:{owner}/{repo}.git"


@pytest.fixture
def private_key_path(tmp_path_factory):
    return str(tmp_path_factory.mktemp(__name__).joinpath("hubcast.key"))


@pytest.fixture
def private_key(private_key_path):
    key = "private_key"
    with open(private_key_path, "w") as fh:
        fh.write(key)
    return key


@pytest.fixture
def hubcast_config(url, private_key_path, private_key):
    from hubcast.config import settings

    settings.github.url = url
    settings.github.private_key_path = private_key_path
    return settings


@pytest.fixture
def hubcast_repo_name():
    return "foo_repo"


@pytest.fixture
def hubcast_repo_factory(hubcast_repo_name):
    def _factory(config):
        return HubcastRepo(
            name=hubcast_repo_name,
            config=config,
        )

    return _factory
