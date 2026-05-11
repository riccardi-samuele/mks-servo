"""HIL: MotorBus.scan() probes addresses on the real bus. Requires the rig.
Assumes exactly one driver, at the slave_addr given in config.toml."""
import pytest

pytestmark = pytest.mark.hil


def test_scan_finds_the_configured_motor(hil_bus, hil_serial_cfg):
    addr = hil_serial_cfg["slave_addr"]
    # Probe a small window around the known address (keep it tight: each empty
    # address costs one `timeout` second).
    lo = max(1, addr - 1)
    hi = addr + 2
    entries = hil_bus.scan(range(lo, hi), timeout=0.5)

    found = [e for e in entries if e.addr == addr]
    assert len(found) == 1, f"expected the motor at addr {addr}, got {[e.addr for e in entries]}"
    e = found[0]
    assert e.model == "servo42d"
    assert isinstance(e.config, dict)
    # read_all_config() populated the common fields:
    assert e.config.get("slave_addr") == addr
    assert e.config.get("subdivision", 0) > 0
    assert e.config.get("current_ma", 0) > 0


def test_scan_empty_address_is_silently_skipped(hil_bus, hil_serial_cfg):
    """An address with no driver must not appear in the results and must not
    raise — scan() swallows CommTimeout per-address."""
    addr = hil_serial_cfg["slave_addr"]
    # Pick an address that is very unlikely to be in use.
    empty_addr = 1 if addr != 1 else 200  # if motor is at 1, probe 200 instead
    entries = hil_bus.scan([empty_addr], timeout=0.5)
    assert [e.addr for e in entries] == []
