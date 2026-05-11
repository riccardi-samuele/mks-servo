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


@pytest.fixture
def hil_serial_cfg():
    """The [serial] table from config.toml as a dict: port, baud, slave_addr, timeout."""
    cfg_path = Path(__file__).parents[2] / "config.toml"
    with cfg_path.open("rb") as f:
        cfg = tomllib.load(f)
    s = cfg["serial"]
    return {
        "port": s["port"],
        "baud": int(s["baud"]),
        "slave_addr": int(s["slave_addr"]),
        "timeout": float(s["timeout"]),
    }


@pytest.fixture
def hil_bus(hil_serial_cfg):
    """An open MotorBus on the rig's serial port. Closed on teardown."""
    from mks_servo import MotorBus
    bus = MotorBus(
        port=hil_serial_cfg["port"],
        baud=hil_serial_cfg["baud"],
        timeout=hil_serial_cfg["timeout"],
    )
    bus.open()
    try:
        yield bus
    finally:
        bus.close()
