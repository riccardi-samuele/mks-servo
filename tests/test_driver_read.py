from unittest.mock import MagicMock, patch
import pytest
from mks_servo.driver import MKSServo42D


@pytest.fixture
def fake_serial(mocker):
    """Patch serial.Serial to return a MagicMock; tests configure its .read return."""
    fake = MagicMock()
    fake.in_waiting = 0
    mocker.patch("mks_servo.driver.serial.Serial", return_value=fake)
    return fake


def test_driver_opens_serial_with_correct_params(fake_serial):
    m = MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1)
    m.open()
    from mks_servo import driver as drv
    drv.serial.Serial.assert_called_once_with(
        port="/dev/ttyUSB0", baudrate=38400, bytesize=8, parity="N", stopbits=1, timeout=0.5,
    )


def test_driver_context_manager_closes_serial(fake_serial):
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m._ser is fake_serial
    fake_serial.close.assert_called_once()


def test_driver_context_manager_disables_motor_on_exit(fake_serial):
    """Safety: __exit__ must send enable=0 if the motor was enabled."""
    fake_serial.read.return_value = bytes.fromhex("FB 01 F3 01 F0")
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        m._enabled = True  # pretend the user called enable(True)
    # Look for an enable(False) frame: FA 01 F3 00 EE
    writes = [c.args[0] for c in fake_serial.write.call_args_list]
    assert any(w.startswith(b"\xfa\x01\xf3\x00") for w in writes)
