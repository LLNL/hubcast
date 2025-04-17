import os


class Config:
    def __init__(self):
        self.port = int(os.environ.get("HC_PORT") or 8080)

        self.account_map_type = os.environ.get("HC_ACCOUNT_MAP_TYPE")
        self.account_map_path = os.environ.get("HC_ACCOUNT_MAP_PATH")

        self.gh = GitHubConfig()
        self.gl = GitLabConfig()


class GitHubConfig:
    def __init__(self):
        self.app_id = os.environ.get("HC_GH_APP_IDENTIFIER")
        self.privkey = os.environ.get("HC_GH_PRIVATE_KEY")
        self.requester = os.environ.get("HC_GH_REQUESTER")
        self.webhook_secret = os.environ.get("HC_GH_SECRET")


class GitLabConfig:
    def __init__(self):
        self.instance_url = os.environ.get("HC_GL_URL")
        self.access_token = os.environ.get("HC_GL_ACCESS_TOKEN")
        self.webhook_secret = os.environ.get("HC_GL_SECRET")
