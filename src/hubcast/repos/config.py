from typing import Dict


class Config:
    def __init__(
        self,
        fullname: str,
        dest_owner: str,
        dest_name: str,
        check_name: str = "gitlab-ci",
        check_type: str = "pipeline",
        create_mr: bool = False,
        delete_closed: bool = True,
    ):
        self.fullname = fullname
        self.dest_owner = dest_owner
        self.dest_name = dest_name
        self.check_name = check_name
        self.check_type = check_type
        self.create_mr = create_mr
        self.delete_closed = delete_closed


class ConfigCache:
    """could be accomplished with async safe dictionary"""

    repos: Dict[str, Config] = dict()

    def __update__(self, fullname: str, config: Config):
        self.repos.update(fullname, config)

    def __get__(self, fullname: str) -> Config:
        return self.repos.get(fullname)


cache = ConfigCache()
