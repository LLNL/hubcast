import os
from typing import Optional


class ConfigError(Exception):
    pass


class Config:
    def __init__(self):
        self.port = int(env_get("HC_PORT", default="8080"))

        self.account_map_type = env_get("HC_ACCOUNT_MAP_TYPE")
        self.account_map_path = env_get("HC_ACCOUNT_MAP_PATH")
        self.logging_config_path = env_get("HC_LOGGING_CONFIG_PATH")

        self.gh = GitHubConfig()
        self.gl = GitLabConfig()


class GitHubConfig:
    def __init__(self):
        self.app_id = env_get("HC_GH_APP_IDENTIFIER")
        self.privkey = env_get("HC_GH_PRIVATE_KEY")
        self.requester = env_get("HC_GH_REQUESTER")
        self.webhook_secret = env_get("HC_GH_SECRET")
        self.bot_user = env_get("HC_GH_BOT_USER")


class GitLabConfig:
    def __init__(self):
        self.instance_url = env_get("HC_GL_URL")
        self.access_token = env_get("HC_GL_ACCESS_TOKEN")
        self.webhook_secret = env_get("HC_GL_SECRET")
        self.callback_url = env_get("HC_GL_CALLBACK_URL")


def env_get(key: str, default: Optional[str] = None) -> str:
    value = os.environ.get(key) or default
    if not value:
        raise ConfigError(f"Required environment variable not found: {key}")

    return value
