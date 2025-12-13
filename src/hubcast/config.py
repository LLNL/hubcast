import logging
import os
import sys
from typing import Optional

log = logging.getLogger(__name__)


class ConfigError(Exception):
    pass


class Config:
    def __init__(self):
        self.port = int(env_get("HC_PORT", default="8080"))

        self.account_map_type = env_get("HC_ACCOUNT_MAP_TYPE")
        self.account_map_path = env_get("HC_ACCOUNT_MAP_PATH")
        self.logging_config_path = env_get("HC_LOGGING_CONFIG_PATH")
        self.src_forge = env_get("HC_SRC_FORGE", "").lower()

        if self.src_forge == "github":
            self.gh_src = GitHubSrcConfig()
        elif self.src_forge == "gitlab":
            self.gl_src = GitLabSrcConfig()
        else:
            log.error('the source forge can only be one of "gitlab" or "github"')
            sys.exit(1)

        self.gl_dest = GitLabDestConfig()


class GitHubSrcConfig:
    def __init__(self):
        self.app_id = env_get("HC_GH_SRC_APP_IDENTIFIER")
        self.privkey = env_get("HC_GH_SRC_PRIVATE_KEY")
        self.requester = env_get("HC_GH_SRC_REQUESTER")
        self.webhook_secret = env_get("HC_GH_SRC_WEBHOOK_SECRET")
        self.bot_user = env_get("HC_GH_BOT_USER")


class GitLabSrcConfig:
    def __init__(self):
        self.instance_url = env_get("HC_GL_SRC_URL")
        self.access_token = env_get("HC_GL_SRC_ACCESS_TOKEN")
        self.requester = env_get("HC_GL_SRC_REQUESTER")
        self.webhook_secret = env_get("HC_GL_SRC_WEBHOOK_SECRET")


class GitLabDestConfig:
    def __init__(self):
        self.instance_url = env_get("HC_GL_DEST_URL")
        # requester identifies the app making requests, it doesn't
        # perform any auth function but is included in user-agent
        self.requester = env_get("HC_GL_REQUESTER")
        self.token = env_get("HC_GL_DEST_TOKEN")
        self.token_type = env_get("HC_GL_DEST_TOKEN_TYPE", default="impersonation")
        self.webhook_secret = env_get("HC_GL_DEST_SECRET")
        self.callback_url = env_get("HC_GL_DEST_CALLBACK_URL")


def env_get(key: str, default: Optional[str] = None) -> str:
    value = os.environ.get(key) or default
    if not value:
        raise ConfigError(f"Required environment variable not found: {key}")

    return value
