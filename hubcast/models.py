import re
from attrs import define, field
from typing import Dict


@define
class GitHubConfig:
    app_id: str = field()
    requester: str = field()
    url: str = field()
    private_key_path: str = field()
    secret: str = field()
    check_name: str = field()
    owner: str = field()
    repo: str = field()
    private_key: str = field()
    installation_id: str = field(default=None)

    # TODO: The owner and repo attributes assume ssh style urls
    @owner.default
    def _owner(self):
        return re.search(r"(?<=\:)[^\/]*", self.url, re.IGNORECASE).group()

    @repo.default
    def _repo(self):
        return re.search(r"(?<=\/)[^.]*", self.url, re.IGNORECASE).group()

    @private_key.default
    def _private_key(self) -> str:
        """Load private key from file."""

        # TODO: auth code seems to require a private key--confirm this method should fail fast
        with open(self.private_key_path, "r") as handle:
            return handle.read()


@define
class GitLabConfig:
    url: str = field()
    requester: str = field()
    access_token: str = field()
    secret: str = field()


@define
class HubcastRepo:
    """Houses all data for a repo in hubcast including GitHub and GitLab config."""

    # TODO: is name sufficiently unique or should we err on using uuids?
    name: str = field()
    config: dict = field()
    git_repo_path: str = field()
    github_config: GitHubConfig = field()
    gitlab_config: GitLabConfig = field()

    @git_repo_path.default
    def _git_repo_path(self):
        base_path = self.config["GIT"]["base_path"]
        return f"{base_path}/{self.name}"

    @github_config.default
    def _github_config(self):
        return GitHubConfig(**self.config["GITHUB"])

    @gitlab_config.default
    def _gitlab_config(self):
        return GitLabConfig(**self.config["GITLAB"])


@define
class HubcastRepoCache:
    _repos: Dict[str, HubcastRepo] = field(factory=dict)

    def get(self, name: str, config: dict) -> HubcastRepo:
        if name not in self._repos:
            self._repos[name] = HubcastRepo(name=name, config=config)

        return self._repos[name]
