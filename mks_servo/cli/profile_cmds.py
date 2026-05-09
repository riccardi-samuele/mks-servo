"""Profile subcommands. Filled in by Tasks 26-29 of the v0.1.0 plan."""
from __future__ import annotations

from pathlib import Path
import click

from mks_servo.profile import Profile
from mks_servo.exceptions import ProfileError


@click.command()
@click.argument("template_name")
@click.option("--as", "as_id", required=True,
              help="Profile id (also used as filename stem)")
@click.option("--out", type=click.Path(),
              help="Output path (default: ./profiles/<id>.yaml)")
@click.option("--force", is_flag=True, help="Overwrite existing file")
def from_template_cmd(template_name: str, as_id: str,
                      out: str | None, force: bool) -> None:
    """Create a new profile from a built-in template."""
    target = Path(out) if out else Path.cwd() / "profiles" / f"{as_id}.yaml"
    if target.exists() and not force:
        raise click.ClickException(
            f"file exists: {target} (pass --force to overwrite)"
        )
    try:
        prof = Profile.from_template(template_name, id=as_id)
    except ProfileError as e:
        raise click.ClickException(str(e)) from e
    prof.save(target)
    click.echo(f"created {target}")


# Other stubs remain (will be replaced in Tasks 27-29)
@click.command()
def from_driver_cmd() -> None:
    """(Stub — implemented in Task 27.)"""
    raise NotImplementedError("from-driver: implemented in Task 27")


@click.command()
def validate_cmd() -> None:
    """(Stub — implemented in Task 28.)"""
    raise NotImplementedError("validate: implemented in Task 28")


@click.command()
def show_cmd() -> None:
    """(Stub — implemented in Task 29.)"""
    raise NotImplementedError("show: implemented in Task 29")
