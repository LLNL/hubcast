# Contributing
## Introduction
Hubcast welcomes contributions via [Pull Requests](https://github.com/LLNL/hubcast/pulls).
We've labeled beginner friendly (good first issue) tasks in the issue tracker, feel free
to reach out and ask for help when getting started.

For small changes (e.g. bug fixes), feel free to submit a PR.

For larger architectual changes and new features, consider opening an
[issue](https://github.com/LLNL/hubcast/issues/new?template=issue-feature-request.md) outlining your
proposed contribution.

## Prerequisites
Hubcast is written in python. You'll need a version of python and pip to
install the required dependencies and nodejs to install the
[smee-client](https://www.npmjs.com/package/smee-client) to test the application locally.

You can install the full development environment using [Spack](spack-develop.md).

## Development
After cloning the repository you'll need to follow the [Getting Started](getting-started.md)
documentation to setup a testing,
1. GitHub Repo
2. GitHub App
3. GitLab Repo
4. GitLab Repo Webhook
5. GitLab Repo Access Token

> [!TIP]
> If you're developing locally you can use [smee.io](https://smee.io) to relay
> webhooks to your local machine. Just click "Start a new channel" & then run
> the following substituting your channel url as the argument and GitHub App
> endpoint.
>
> ```bash
> $ smee -u https://smee.io/reDaCTed
> ```

## Project Structure
```bash
.
├── LICENSE
├── README.md
├── docs # ---------> project documentation
├── hubcast # ------> python application
├── pyproject.toml
├── spack.lock
└── spack.yaml -----> spack development environment
```
```bash
hubcast
├── __main__.py # --> hubcast entrypoint and config setup
├── auth # ---------> authentication library for GitHub/GitLab
├── github.py # ----> GitHub router setup
├── gitlab.py # ----> GitLab router setup
├── routes # -------> GitHub & GitLab event routing logic
└── utils # --------> Git and common application utilities
```
