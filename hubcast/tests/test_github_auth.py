import pytest
from unittest import mock

from hubcast.auth.github import App


@pytest.fixture
def app_id():
    return "abc123"


@pytest.fixture
def installation_id():
    return "installation123"


@pytest.fixture
def requester():
    return "hubcast-bot"


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
def jwt():
    return "jwt123"


@pytest.fixture
def iso_8601_timestamp():
    return "2023-12-28T22:27:06Z"


@pytest.fixture
def access_token():
    return "access123"


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
def github_config(app_id, requester, url, private_key_path):
    from hubcast.config import settings

    config = settings.github.to_dict()
    config["app_id"] = app_id
    config["requester"] = requester
    config["repo"] = url
    config["private_key_path"] = private_key_path
    return config


@pytest.fixture
def app_factory():
    def _factory(config):
        return App(
            id=config["app_id"],
            requester=config["requester"],
            url=config["repo"],
            private_key_path=config["private_key_path"],
        )

    return _factory


def test_dynamic_app_attributes(app_factory, github_config, owner, repo, private_key):
    # Setup/Execute
    app = app_factory(github_config)

    assert app.owner == owner
    assert app.repo == repo
    assert app.private_key == private_key


@mock.patch("hubcast.auth.github.gha")
async def test_get_jwt(mock_gha, app_factory, github_config, jwt, app_id, private_key):
    # Setup
    mock_gha.get_jwt.return_value = jwt
    app = app_factory(github_config)

    # Execute
    actual_jwt = await app.get_jwt()

    # Verify
    assert actual_jwt == jwt
    mock_gha.get_jwt.assert_called_once_with(app_id=app_id, private_key=private_key)


@mock.patch("hubcast.auth.github.gha")
@mock.patch("hubcast.auth.github.gh_aiohttp.GitHubAPI")
async def test_get_installation_id(
    MockGitHubAPI,
    mock_gha,
    app_factory,
    github_config,
    jwt,
    installation_id,
    app_id,
    private_key,
):
    # Setup
    mock_gha.get_jwt.return_value = jwt
    mock_gh = MockGitHubAPI.return_value
    mock_gh.getitem = mock.AsyncMock()
    mock_gh.getitem.return_value = {"id": installation_id}
    app = app_factory(github_config)

    # Execute
    actual_installation_id = await app.get_installation_id()

    # Verify
    assert actual_installation_id == installation_id
    mock_gh.getitem.assert_awaited_with(
        f"/repos/{app.owner}/{app.repo}/installation",
        accept="application/vnd.github+json",
        jwt=jwt,
    )

    # Execute
    mock_gh.getitem.reset_mock()
    actual_installation_id = await app.get_installation_id()

    # Verify: second call returns cached result
    assert actual_installation_id == installation_id
    mock_gh.getitem.assert_not_awaited()


@mock.patch("hubcast.auth.github.gha")
@mock.patch("hubcast.auth.github.gh_aiohttp.GitHubAPI")
async def test_authenticate_installation(
    MockGitHubAPI,
    mock_gha,
    app_factory,
    github_config,
    jwt,
    installation_id,
    iso_8601_timestamp,
    access_token,
    app_id,
    private_key,
):
    # Setup
    mock_gha.get_jwt.return_value = jwt
    mock_gh = MockGitHubAPI.return_value
    mock_gh.post = mock.AsyncMock()
    mock_gh.post.return_value = {
        "token": access_token,
        "expires_at": iso_8601_timestamp
    }
    mock_gh.getitem = mock.AsyncMock()
    mock_gh.getitem.return_value = {"id": installation_id}
    app = app_factory(github_config)

    # Execute
    actual_access_token = await app.authenticate_installation()

    # Verify
    assert actual_access_token == access_token
    mock_gh.post.assert_awaited_with(
        "app/installations/{installation_id}/access_tokens",
        {"installation_id": installation_id},
        data=b"",
        accept="application/vnd.github.machine-man-preview+json",
        jwt=jwt,
    )
