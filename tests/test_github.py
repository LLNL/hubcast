import pytest
from dataclasses import dataclass
from unittest import mock

from hubcast.routes import github


@dataclass
class Event:
    data: dict


@pytest.fixture
def pr_number():
    return 1234


@pytest.fixture
def pr_event_factory():
    def _factory(number):
        data = {"pull_request": {"number": number}}
        return Event(data=data)

    return _factory


@mock.patch("hubcast.routes.github.git")
async def test_github_sync_pr(mock_git, pr_number, pr_event_factory):
    # Setup
    event = pr_event_factory(pr_number)

    # Execute
    await github.sync_pr(event, mock.Mock())

    # Assert
    mock_git.assert_has_calls(
        [
            mock.call(f"fetch github pull/{pr_number}/head"),
            mock.call(f"push gitlab FETCH_HEAD:refs/heads/pr-{pr_number}"),
        ]
    )


@mock.patch("hubcast.routes.github.git")
async def test_github_remove_pr(mock_git, pr_number, pr_event_factory):
    # Setup
    event = pr_event_factory(pr_number)

    # Execute
    await github.remove_pr(event, mock.Mock())

    # Assert
    mock_git.assert_called_once_with(f"push -d gitlab refs/heads/pr-{pr_number}")
