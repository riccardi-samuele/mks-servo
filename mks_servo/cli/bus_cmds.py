"""Bus subcommands: discover."""
from __future__ import annotations

from pathlib import Path
import click

from mks_servo.bus import MotorBus


def _parse_range(s: str) -> range:
    """Parse '1-16' into range(1, 17). Single number 'N' returns range(N, N+1)."""
    if "-" not in s:
        v = int(s)
        return range(v, v + 1)
    a, b = s.split("-", 1)
    return range(int(a), int(b) + 1)


@click.command()
@click.option("--port", required=True, help="Serial port (e.g. /dev/ttyUSB0)")
@click.option("--range", "addr_range", default="1-16",
              help="Address range to probe (e.g. 1-16, 5, 10-20)")
@click.option("--baud", default=38400, type=int)
@click.option("--timeout", default=1.0, type=float,
              help="Per-address probe timeout in seconds")
@click.option("--create-profiles", is_flag=True,
              help="Generate profile YAMLs for each driver found")
@click.option("--out", type=click.Path(), help="Output dir (default: ./profiles)")
@click.option("--force", is_flag=True, help="Overwrite existing profile files")
def discover_cmd(port: str, addr_range: str, baud: int, timeout: float,
                 create_profiles: bool, out: str | None, force: bool) -> None:
    """Scan a bus and report discovered drivers."""
    rng = _parse_range(addr_range)
    output_dir = Path(out) if out else Path.cwd() / "profiles"

    with MotorBus(port=port, baud=baud) as bus:
        entries = bus.scan(rng, create_profiles=create_profiles,
                           output_dir=output_dir, force=force, timeout=timeout)

    if not entries:
        click.echo("no drivers found")
        return

    for e in entries:
        cfg = e.config or {}
        mode_obj = cfg.get("mode")
        mode = getattr(mode_obj, "name", str(mode_obj) if mode_obj is not None else "?")
        cur = cfg.get("current_ma", "?")
        sub = cfg.get("subdivision", "?")
        suffix = ""
        if e.profile is not None and getattr(e.profile, "path", None):
            suffix = f"  → {e.profile.path}"
        click.echo(f"  addr={e.addr}: {e.model}, mode={mode}, "
                   f"current={cur} mA, subdiv={sub}{suffix}")

    click.echo(f"\n{len(entries)} driver(s) found.")
