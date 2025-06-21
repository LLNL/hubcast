from typing import Dict, Union

import yaml

from .abc import AccountMap


class FileMap(AccountMap):
    """
    A simple user map importing from a YAML file of the form:

    Users:
      github_user: gitlab_user
      github_user2: gitlab_user2

    Attributes
    ----------
    path: str
        A filepath to the users.yml defining a user mapping.
    """

    path: str
    users: Dict[str, str]

    def __init__(self, path: str):
        """
        Constructor, path to read from and generate a simple account
        mapping between services (eg gitlab->gitlab or github->gitlab).
        """
        self.path = path

        with open(path, "r") as f:
            try:
                data = yaml.safe_load(f)
                self.users = data["Users"]
            except yaml.YAMLError as exc:
                print(exc)

    def __call__(self, src_user: str) -> Union[str, None]:
        """
        Return the gitlab_user for a src_user if one exists.
        """
        return self.users.get(src_user)
