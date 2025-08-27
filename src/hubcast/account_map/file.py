import logging
from typing import Dict, Union

import yaml

from .abc import AccountMap

log = logging.getLogger(__name__)


class FileMap(AccountMap):
    """
    A simple user map importing from a YAML file of the form.

    Users:
      github_user: gitlab_user
      github_user2: gitlab_user2

    Attributes
    ----------
    path: str
        A filepath to the users.yml defining a usermapping.
    """

    path: str
    users: Dict[str, str]

    def __init__(self, path: str):
        """
        Constructor, path to read from and generate a simple account
        mapping between services.
        """
        self.path = path

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)
                self.users = data["Users"]
        except FileNotFoundError:
            log.error("Account map file not found", extra={"path": path})
        except yaml.YAMLError:
            log.exception("Failed to parse file map YAML", extra={"path": path})

    def __call__(self, github_user: str) -> Union[str, None]:
        """
        Return the gitlab_user for a github_user if one exists.
        """
        return self.users.get(github_user)
