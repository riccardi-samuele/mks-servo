"""Fixtures for HIL tests. Reads /dev/ttyUSB0 settings from config.toml."""
from pathlib import Path
import sys
import pytest

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from mks_servo.profile import Profile, DriverSection, TransportSection


@pytest.fixture
def hil_profile(tmp_path):
    cfg_path = Path(__file__).parents[2] / "config.toml"
    with cfg_path.open("rb") as f:
        cfg = tomllib.load(f)
    s = cfg["serial"]
    p = Profile(
        id="hil_test",
        driver=DriverSection(model="servo42d", slave_addr=int(s["slave_addr"])),
        transport=TransportSection(
            port=s["port"], baud=int(s["baud"]), timeout_s=float(s["timeout"]),
        ),
    )
    return p
