def help_message(bot_user: str):
    return f"""
You can interact with me in many ways!

- `@{bot_user} help`: see this message
- `@{bot_user} approve`: sync this pull request with the destination repository and trigger a new pipeline
- `@{bot_user} run pipeline`: request a new run of the GitLab CI pipeline for any reason

If you are an outside contributor to this repository, a maintainer will need to approve and run pipelines on your behalf.

For assistance and bug reports, open an issue [here](https://github.com/llnl/hubcast/issues).
"""
