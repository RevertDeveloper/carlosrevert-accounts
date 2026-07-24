#!/usr/bin/env python3
"""Django management entry point."""

import os
import sys
from pathlib import Path

import environ


def main() -> None:
    # Settings are selected before Django imports config/settings/base.py, so
    # load the environment here as well for host-side management commands.
    explicit_settings = os.environ.get("DJANGO_SETTINGS_MODULE")
    environ.Env.read_env(Path(__file__).resolve().parent / ".env")
    if len(sys.argv) > 1 and sys.argv[1] == "test" and explicit_settings is None:
        # Las pruebas no deben heredar el storage ni los redirects de producción desde .env.
        os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    else:
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
