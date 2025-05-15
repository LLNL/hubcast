# Getting Started
## Installation
> [!WARNING]
> Hubcast is still in development. Easy installation instructions using PyPI
> and production containers coming soon.

## Configuration
Hubcast may be configured using environment variables.

A full set of the current environment variables are shown below.
For development instances of hubcast it is suggested you save these environment
variables in a `.env` file or similar and source it before execution.

##### .env
```
#------------------------------------------------------------------------
# Git Repository Settings
#------------------------------------------------------------------------
# Path for a local Git repository used as an intermediate sync.
export HC_GIT_REPO_PATH=""

# Remote GitHub Repository.
export HC_GH_REPO=""

# Remote GitLab Repository.
export HC_GL_REPO=""

#------------------------------------------------------------------------
# GitHub Settings
#------------------------------------------------------------------------
# Name of the GitHub check to be displayed for GitLab Ci Runs.
export HC_GH_CHECK_NAME=""

# GitHub App Webhook Secret.
export HC_GH_SECRET=""

# Path to GitHub App's private key. Used for generating tokens.
export HC_GH_PRIVATE_KEY_PATH=""

# GitHub User to act on the behalf of.
export HC_GH_REQUESTER=""

# GitHub App Identifier. (Numerical ID.)
export HC_GH_APP_IDENTIFIER=

#------------------------------------------------------------------------
# GitLab Settings
#------------------------------------------------------------------------
# Authentication token for interacting with GitLab.
export HC_GL_ACCESS_TOKEN=""

# GitLab Webhook Secret.
export HC_GL_SECRET=""

# GitLab User to act on the behalf of.
export HC_GL_REQUESTER=""

#------------------------------------------------------------------------
# Account Map Settings
#------------------------------------------------------------------------
export HC_ACCOUNT_MAP_PATH="users.yml"

#------------------------------------------------------------------------
# General Bot Settings
#------------------------------------------------------------------------
# Port for hubcast to listen on.
export HC_PORT=3000
```
### Creating a GitHub Repo to Mirror
If you don't already have a GitHub repository you'd like to mirror, you'll
need to create a new repository. (When setting up Hubcast for the first time
it may be a good idea to test it first on a test repository.)

> [!TIP]
> If you're setting up a local instance of Hubcast to develop on we recommend
> setting up a hubcast-test repository to test out your changes before
> submitting a PR. To create a test repository click
> [here](https://github.com/new?name=hubcast-test).


### Creating a GitHub App
To create a GitHub App you'll need a callback url and a webhook secret.

If you're deploying Hubcast in production, this callback url be an https link
to your infrastructure. If you're deploying for development, we recommend
using [smee.io](https://smee.io) to forward webhooks to your local environment.

To see more about contributing to Hubcast check out our contributing
guide [here](contributing.md).

Your webhook secret should be a shared complex string allowing you to verify
webhooks came from GitHub. To generate a complex secret you can run,

```bash
$ openssl rand -base64 24
```

With a callback url and secret handy follow GitHub's
[Registering a GitHub App](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app#registering-a-github-app)
guide to create your app installation.

We should now be able to fill in the following environment variables in
Hubcast's configuration with the values retrieved from GitHub's setup.

##### .env
```
#------------------------------------------------------------------------
# GitHub Settings
#------------------------------------------------------------------------
# Name of the GitHub check to be displayed for GitLab Ci Runs.
export HC_GH_CHECK_NAME=""

# GitHub App Webhook Secret.
export HC_GH_SECRET=""

# Path to GitHub App's private key you downloaded from GitHub.
# Used for generating tokens.
export HC_GH_PRIVATE_KEY_PATH=""

# GitHub User to act on the behalf of.
export HC_GH_REQUESTER=""

# GitHub App Identifier. (Numerical ID Shown on GitHub App Config Page.)
export HC_GH_APP_IDENTIFIER=
```

### Creating a GitLab Repository
If you don't already have a GitLab repository you'd like to mirror into,
we'll need to create one at this point.

> [!TIP]
> If you're setting up a local instance of Hubcast to develop on we recommend
> setting up a hubcast-test repository to test out your changes before
> submitting a PR. To create a test repository on GitLab.com click
> [here](https://gitlab.com/projects/new).

### Creating a GitLab Webhook
Once we've setup a new blank repository in GitLab we can configure it with a
webhook. This webhook will notify Hubcast of in-progress, completed, and failed
CI jobs so those statuses may be passed back to the GitHub Repository.

Before configuring the webhook in GitLab we'll need to have our callback url handy
and generate another webhoook secret.

```bash
$ openssl rand -base64 24
```

One you've got those two values you can follow GitLab's instructions in the
[Webhooks docs](https://docs.gitlab.com/ee/user/project/integrations/webhooks.html#configure-a-webhook-in-gitlab).

> [!TIP]
> Make sure to set the webhook to trigger on both `job events` and `pipeline events`.

### Creating a GitLab Project Access Token
Finally to access the GitLab API we'll need to create Project Access Token
inside the repository by following the instructions
[here](https://docs.gitlab.com/ee/user/project/settings/project_access_tokens.html#create-a-project-access-token).

> [!TIP]
> To ensure Hubcast can operate successfully you'll need to give the following permissions
> to the project access token,
> - `read_api`
> - `read_repository`
> - `write_repository`

### Completing the GitLab Configuration
After creating the GitLab repository, webhook, and access token we can now fill out the
remainder of the Hubcast GitLab config.

##### .env
```bash
#------------------------------------------------------------------------
# GitLab Settings
#------------------------------------------------------------------------
# Authentication token for interacting with GitLab.
export HC_GL_ACCESS_TOKEN=""

# GitLab Webhook Secret.
export HC_GL_SECRET=""

# GitLab User to act on the behalf of.
export HC_GL_REQUESTER=""
```

### Creating a Account Map Document
Lastly we'll need to create a simple account map to map GitHub to GitLab users.

##### .env
```bash
#------------------------------------------------------------------------
# Account Map Settings
#------------------------------------------------------------------------
export HC_ACCOUNT_MAP_PATH="users.yml"
```

##### users.yml
```yaml
Users:
  github_user1: gitlab_user1
  github_user2: gitlab_user2
  ...
```

### Finishing Up
At this point we should now be able to launch our instance of hubcast
and have it begin mirroring events from GitHub to GitLab.

```bash
$ source .env
$ python -m hubcast
```
