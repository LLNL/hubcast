from .auth import GitLabAuthenticator


class GitLabClientFactory:
    def __init__(self, instance_url, access_token):
        self.auth = GitLabAuthenticator(instance_url, access_token)
        self.instance_url = instance_url


class GitLabClient:
    def __init__(self, auth):
        self.auth = auth
