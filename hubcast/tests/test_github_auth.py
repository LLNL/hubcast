import pytest
from unittest import mock

from hubcast.auth.github import get_jwt, get_installation_id, authenticate_installation


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
def jwt():
    return "jwt123"


@pytest.fixture
def iso_8601_timestamp():
    return "2023-12-28T22:27:06Z"


@pytest.fixture
def access_token():
    return "access123"


@pytest.fixture
def config(app_id, requester, url, private_key_path, private_key):
    from hubcast.config import settings

    settings.github.app_id = app_id
    settings.github.requester = requester
    settings.github.url = url
    settings.github.private_key_path = private_key_path
    return settings.to_dict()


@mock.patch("hubcast.auth.github.gha")
async def test_get_jwt(
    mock_gha, hubcast_repo_factory, config, jwt, app_id, private_key
):
    # Setup
    mock_gha.get_jwt.return_value = jwt
    hubcast_repo = hubcast_repo_factory(config)

    # Execute
    actual_jwt = await get_jwt(hubcast_repo.github_config)

    # Verify
    assert actual_jwt == jwt
    mock_gha.get_jwt.assert_called_once_with(app_id=app_id, private_key=private_key)


@mock.patch("hubcast.auth.github.gha")
@mock.patch("hubcast.auth.github.gh_aiohttp.GitHubAPI")
async def test_get_installation_id(
    MockGitHubAPI,
    mock_gha,
    hubcast_repo_factory,
    config,
    owner,
    repo,
    jwt,
    installation_id,
    app_id,
):
    # Setup
    mock_gha.get_jwt.return_value = jwt
    mock_gh = MockGitHubAPI.return_value
    mock_gh.getitem = mock.AsyncMock()
    mock_gh.getitem.return_value = {"id": installation_id}
    hubcast_repo = hubcast_repo_factory(config)

    # Execute
    actual_installation_id = await get_installation_id(mock.Mock(), hubcast_repo.github_config)

    # Verify
    assert actual_installation_id == installation_id
    mock_gh.getitem.assert_awaited_with(
        f"/repos/{owner}/{repo}/installation",
        accept="application/vnd.github+json",
        jwt=jwt,
    )


@mock.patch("hubcast.auth.github.gha")
@mock.patch("hubcast.auth.github.gh_aiohttp.GitHubAPI")
async def test_authenticate_installation(
    MockGitHubAPI,
    mock_gha,
    hubcast_repo_factory,
    config,
    jwt,
    installation_id,
    iso_8601_timestamp,
    access_token,
    app_id,
):
    # Setup
    mock_gha.get_jwt.return_value = jwt
    mock_gh = MockGitHubAPI.return_value
    mock_gh.post = mock.AsyncMock()
    mock_gh.post.return_value = {
        "token": access_token,
        "expires_at": iso_8601_timestamp,
    }
    mock_gh.getitem = mock.AsyncMock()
    mock_gh.getitem.return_value = {"id": installation_id}

    hubcast_repo = hubcast_repo_factory(config)
    hubcast_repo.github_config.installation_id = installation_id

    # Execute
    actual_access_token = await authenticate_installation(mock.Mock(), hubcast_repo.github_config)

    # Verify
    assert actual_access_token == access_token
    mock_gh.post.assert_awaited_with(
        "app/installations/{installation_id}/access_tokens",
        {"installation_id": installation_id},
        data=b"",
        accept="application/vnd.github.machine-man-preview+json",
        jwt=jwt,
    )
