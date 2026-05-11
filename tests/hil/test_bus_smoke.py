"""HIL: a Motor obtained via MotorBus.add() drives real hardware through the
shared transport. Requires the rig (single motor at slave_addr from config.toml)."""
import pytest

pytestmark = pytest.mark.hil


def test_bus_add_motor_moves_and_reads_back(hil_bus, hil_profile):
    motor = hil_bus.add(hil_profile)
    assert len(hil_bus) == 1
    assert motor in hil_bus

    # Tolerance ≈2σ of this rig's repeatability (σ≈0.82°): "landed roughly
    # here", not a precision check (that's what test_characterize.py does).
    motor.set_origin()
    motor.write(0)
    assert abs(motor.read()) < 1.5

    motor.write(45, rpm=300)
    assert abs(motor.read() - 45.0) < 1.5

    motor.write(0)
    assert abs(motor.read()) < 1.5


def test_bus_motor_shares_transport_object(hil_bus, hil_profile):
    """The Motor's RawDriver must reference the bus's SharedTransport, not a
    private serial.Serial — that's the whole point of the bus."""
    motor = hil_bus.add(hil_profile)
    assert motor.raw._transport is hil_bus._transport
    assert motor.raw._owns_transport is False
