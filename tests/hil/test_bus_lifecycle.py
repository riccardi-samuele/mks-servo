"""HIL: MotorBus lifecycle on real hardware — add, remove, re-add, close.
Requires the rig (single motor)."""
import pytest

pytestmark = pytest.mark.hil


# Position tolerance ≈2σ of this rig's repeatability (σ≈0.82°): these are
# "the move landed roughly here" sanity checks, not precision checks.
_POS_TOL_DEG = 1.5


def test_remove_then_readd_works(hil_bus, hil_profile):
    m1 = hil_bus.add(hil_profile)
    # write() targets an absolute axis position relative to the firmware zero
    # (cmd 0x92), which other tests in the suite move around — pin it here so
    # this test is order-independent.
    m1.set_origin()
    m1.write(20)
    assert abs(m1.read() - 20.0) < _POS_TOL_DEG

    hil_bus.remove(m1)
    assert len(hil_bus) == 0
    assert m1._attached is False

    # Re-adding the same profile must produce a working motor again.
    m2 = hil_bus.add(hil_profile)
    assert len(hil_bus) == 1
    m2.write(0)
    assert abs(m2.read()) < _POS_TOL_DEG


def test_bus_context_manager_closes_transport_and_disables(hil_serial_cfg, hil_profile):
    """Exiting the `with` block must disable the motor and close the serial port."""
    from mks_servo import MotorBus
    with MotorBus(port=hil_serial_cfg["port"], baud=hil_serial_cfg["baud"],
                  timeout=hil_serial_cfg["timeout"]) as bus:
        m = bus.add(hil_profile)
        m.set_origin()  # pin the firmware zero (see note in test above)
        m.write(10)
        assert abs(m.read() - 10.0) < _POS_TOL_DEG
        assert bus._transport._ser is not None
        raw = m.raw
    # After the block: transport closed, motor was detached (disabled).
    assert bus._transport._ser is None
    assert getattr(raw, "_enabled", False) is False
