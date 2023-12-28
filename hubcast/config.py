"""Hubcast config."""
from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="HC",
    settings_files=['settings.toml', '.secrets.toml'],
    environments=True,
)
