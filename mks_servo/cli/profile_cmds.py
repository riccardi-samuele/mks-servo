"""Profile subcommands. Filled in by Tasks 26-29 of the v0.1.0 plan."""
from __future__ import annotations

from pathlib import Path
import click

from mks_servo.profile import Profile
from mks_servo.exceptions import ProfileError
from mks_servo.raw import RawDriver


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
@click.option("--port", required=True, help="Serial port, e.g. /dev/ttyUSB0")
@click.option("--addr", required=True, type=int, help="Slave address (1..247)")
@click.option("--baud", default=38400, type=int)
@click.option("--timeout", default=3.0, type=float, help="Serial timeout in seconds")
@click.option("--as", "as_id", required=True, help="Profile id")
@click.option("--out", type=click.Path(), help="Output path")
@click.option("--force", is_flag=True)
def from_driver_cmd(port: str, addr: int, baud: int, timeout: float,
                    as_id: str, out: str | None, force: bool) -> None:
    """Snapshot a connected driver into a new profile."""
    target = Path(out) if out else Path.cwd() / "profiles" / f"{as_id}.yaml"
    if target.exists() and not force:
        raise click.ClickException(
            f"file exists: {target} (pass --force to overwrite)"
        )

    raw = RawDriver(port=port, baud=baud, addr=addr, timeout=timeout)
    try:
        # Open the serial transport (RawDriver doesn't auto-open in __init__).
        opener = getattr(raw, "open", None)
        if callable(opener):
            opener()
        prof = Profile.from_driver(raw, id=as_id)
        prof.transport.port = port
    finally:
        close = getattr(raw, "close", None)
        if callable(close):
            close()
    prof.save(target)
    click.echo(f"created {target}")


@click.command()
def validate_cmd() -> None:
    """(Stub — implemented in Task 28.)"""
    raise NotImplementedError("validate: implemented in Task 28")


@click.command()
def show_cmd() -> None:
    """(Stub — implemented in Task 29.)"""
    raise NotImplementedError("show: implemented in Task 29")
