class RepoConfig:
    def __init__(
        self,
        fullname: str,
        dest_org: str,
        dest_name: str,
        check_name: str = "gitlab-ci",
        check_type: str = "pipeline",
        create_mr: bool = False,
        delete_closed: bool = True,
    ):
        self.fullname = fullname
        self.dest_org = dest_org
        self.dest_name = dest_name
        self.check_name = check_name
        self.check_type = check_type
        self.create_mr = create_mr
        self.delete_closed = delete_closed
