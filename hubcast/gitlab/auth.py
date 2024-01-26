class GitLabAuthenticator:
    def __init__(self, instance_url, access_token=None):
        self.instance_url = instance_url
        self.access_token = access_token

    async def authenticate_installation(self, username):
        return self.access_token
