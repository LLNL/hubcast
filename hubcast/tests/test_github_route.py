import pytest
from unittest import mock

from hubcast.routes import github


@pytest.fixture
def pr_number():
    return 1234


@pytest.fixture
def pr_event_factory():
    def _factory(number):
        event = mock.Mock()
        event.data = {"pull_request": {"number": number}}
        return event

    return _factory


@pytest.fixture
def hubcast_repo(hubcast_repo_factory, hubcast_config):
    return hubcast_repo_factory(config=hubcast_config)


@pytest.fixture
def mock_git_config():
    return {"repo_path": "/"}


@pytest.fixture
def mock_git():
    with mock.patch("hubcast.routes.github.Git") as MockGit:
        yield MockGit.return_value


async def test_github_sync_pr(
    mock_git_config, mock_git, hubcast_repo, pr_number, pr_event_factory
):
    # Setup
    event = pr_event_factory(pr_number)

    # Execute
    await github.sync_pr(event, hubcast_repo, mock.Mock())

    # Verify
    mock_git.assert_has_calls(
        [
            mock.call(f"fetch github pull/{pr_number}/head"),
            mock.call(f"push gitlab FETCH_HEAD:refs/heads/pr-{pr_number}"),
        ]
    )


async def test_github_remove_pr(
    mock_git_config, mock_git, hubcast_repo, pr_number, pr_event_factory
):
    # Setup
    event = pr_event_factory(pr_number)

    # Execute
    await github.remove_pr(event, hubcast_repo, mock.Mock())

    # Verify
    mock_git.assert_called_once_with(f"push -d gitlab refs/heads/pr-{pr_number}")
