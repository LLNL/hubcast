from unittest import mock

import pytest
from gidgethub import sansio

from hubcast.github.routes import router as gh_router


@pytest.fixture
def pr_event_factory():
    def _factory(action, delivery_id, number):
        payload = {"action": action, "pull_request": {"number": number}}
        event = sansio.Event(payload, event="pull_request", delivery_id=delivery_id)
        return event

    return _factory


@pytest.fixture
async def m_repo_lock():
    m = mock.AsyncMock()
    mock.patch("asyncio.Lock", return_value=m)
    return m


@mock.patch("gidgethub.aiohttp.GitHubAPI")
@mock.patch("gidgetlab.aiohttp.GitLabAPI")
@mock.patch("hubcast.utils.git.Git")
async def test_github_sync_pr(m_gh, m_gl, m_git, m_repo_lock, pr_event_factory):
    # Setup
    event = pr_event_factory("opened", "1", "1234")

    # Execute
    await gh_router.dispatch(event, m_gh, m_gl, m_git, m_repo_lock)

    # Assert
    m_git.assert_has_calls(
        [
            mock.call(["fetch", "github", "pull/1234/head"]),
            mock.call(["push", "gitlab", "FETCH_HEAD:refs/heads/pr-1234"]),
        ]
    )


@mock.patch("gidgethub.aiohttp.GitHubAPI")
@mock.patch("gidgetlab.aiohttp.GitLabAPI")
@mock.patch("hubcast.utils.git.Git")
async def test_github_remove_pr(m_gh, m_gl, m_git, m_repo_lock, pr_event_factory):
    # Setup
    event = pr_event_factory("closed", "2", "1234")

    # Execute
    await gh_router.dispatch(event, m_gh, m_gl, m_git, m_repo_lock)

    # Assert
    m_git.assert_called_once_with(["push", "-d", "gitlab", "refs/heads/pr-1234"])
