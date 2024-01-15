import subprocess


# https://git-scm.com/docs/gitcredentials#_custom_helpers
def credential_helper(remote: str) -> str:
    remote = remote.upper()
    return f"""!f() {{ echo "username=${remote}_USERNAME"; echo "password=${remote}_TOKEN"; }};f"""


class Git:
    def __init__(
        self,
        repo_path: str,
        gh_username: str,
        gh_token: str,
        gl_username: str,
        gl_token: str,
        gl_instance_url: str,
    ):
        self.repo_path = repo_path
        self.gl_url = gl_instance_url.removeprefix("https://")

        self.gh_helper = credential_helper("github")
        self.gl_helper = credential_helper("gitlab")

        self.env = {
            "GITHUB_USERNAME": gh_username,
            "GITHUB_TOKEN": gh_token,
            "GITLAB_USERNAME": gl_username,
            "GITLAB_TOKEN": gl_token,
        }

    def __call__(self, cmd: str):
        """Executes a git command on the host system."""
        result = subprocess.run(
            f"git \
             -c credential.github.com.helper='{self.gh_helper}' \
             -c credential.{self.gl_url}.helper='{self.gl_helper}' \
             -C {self.repo_path} {cmd}",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=self.env,
            shell=True,
            text=True,
            check=True,
        )
        return result
