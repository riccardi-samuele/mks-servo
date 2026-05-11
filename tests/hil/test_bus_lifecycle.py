"""HIL: MotorBus lifecycle on real hardware — add, remove, re-add, close.
Requires the rig (single motor)."""
import pytest

pytestmark = pytest.mark.hil


def test_remove_then_readd_works(hil_bus, hil_profile):
    m1 = hil_bus.add(hil_profile)
    m1.write(20)
    assert abs(m1.read() - 20.0) < 1.0

    hil_bus.remove(m1)
    assert len(hil_bus) == 0
    assert m1._attached is False

    # Re-adding the same profile must produce a working motor again.
    m2 = hil_bus.add(hil_profile)
    assert len(hil_bus) == 1
    m2.write(0)
    assert abs(m2.read()) < 1.0


def test_bus_context_manager_closes_transport_and_disables(hil_serial_cfg, hil_profile):
    """Exiting the `with` block must disable the motor and close the serial port."""
    from mks_servo import MotorBus
    with MotorBus(port=hil_serial_cfg["port"], baud=hil_serial_cfg["baud"],
                  timeout=hil_serial_cfg["timeout"]) as bus:
        m = bus.add(hil_profile)
        m.write(10)
        assert abs(m.read() - 10.0) < 1.0
        assert bus._transport._ser is not None
        raw = m.raw
    # After the block: transport closed, motor was detached (disabled).
    assert bus._transport._ser is None
    assert getattr(raw, "_enabled", False) is False
