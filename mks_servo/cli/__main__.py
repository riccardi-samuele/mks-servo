"""mks-servo CLI entry point."""
from __future__ import annotations

import sys
import click

from mks_servo import __version__


@click.group()
@click.version_option(version=__version__, prog_name="mks-servo")
def cli() -> None:
    """mks-servo — manage MKS SERVO motors and profiles."""


@cli.group()
def profile() -> None:
    """Operations on motor profiles (YAML files)."""


# Register subcommands on the profile group.
from mks_servo.cli.profile_cmds import (  # noqa: E402
    from_driver_cmd, from_template_cmd, validate_cmd, show_cmd,
)
profile.add_command(from_driver_cmd, name="from-driver")
profile.add_command(from_template_cmd, name="from-template")
profile.add_command(validate_cmd, name="validate")
profile.add_command(show_cmd, name="show")


def main() -> int:
    return cli(standalone_mode=True)


if __name__ == "__main__":
    sys.exit(main())
