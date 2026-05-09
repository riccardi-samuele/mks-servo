from unittest.mock import MagicMock, patch
import pytest
from mks_servo.raw import RawDriver as MKSServo42D


@pytest.fixture
def fake_serial(mocker):
    """Patch serial.Serial to return a MagicMock; tests configure its .read return."""
    fake = MagicMock()
    fake.in_waiting = 0
    mocker.patch("mks_servo.raw.serial.Serial", return_value=fake)
    return fake


def test_driver_opens_serial_with_correct_params(fake_serial):
    m = MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1)
    m.open()
    from mks_servo import raw as drv
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


def test_read_encoder_returns_carry_and_value(fake_serial):
    fake_serial.read.return_value = bytes.fromhex("FB 01 30 FF FF FF FF 22 69 B3")
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        carry, value = m.read_encoder()
    assert carry == -1
    assert value == 0x2269


def test_read_encoder_addition_returns_int48(fake_serial):
    body = bytes.fromhex("FB 01 31 00 00 00 00 7F FF")
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        value = m.read_encoder_addition()
    assert value == 0x7FFF


def test_read_encoder_addition_negative(fake_serial):
    body = bytes.fromhex("FB 01 31 FF FF FF FF C0 00")
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        value = m.read_encoder_addition()
    assert value == -0x4000


def test_read_speed_rpm_positive(fake_serial):
    body = bytes.fromhex("FB 01 32") + (500).to_bytes(2, "big", signed=True)
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m.read_speed_rpm() == 500


def test_read_speed_rpm_negative(fake_serial):
    body = bytes.fromhex("FB 01 32") + (-1500).to_bytes(2, "big", signed=True)
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m.read_speed_rpm() == -1500


def test_read_pulses(fake_serial):
    body = bytes.fromhex("FB 01 33") + (32000).to_bytes(4, "big", signed=True)
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m.read_pulses() == 32000


def test_read_angle_error_one_degree(fake_serial):
    body = bytes.fromhex("FB 01 39") + (142).to_bytes(4, "big", signed=True)
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m.read_angle_error() == 142


from mks_servo.raw import MotorStatus


def test_read_motor_status_stopped(fake_serial):
    body = bytes.fromhex("FB 01 F1 01")
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m.read_motor_status() == MotorStatus.STOPPED


def test_read_motor_status_full_speed(fake_serial):
    body = bytes.fromhex("FB 01 F1 04")
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m.read_motor_status() == MotorStatus.FULL_SPEED


def test_read_protect_status_protected(fake_serial):
    body = bytes.fromhex("FB 01 3E 01")
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m.read_protect_status() is True


def test_read_protect_status_not_protected(fake_serial):
    body = bytes.fromhex("FB 01 3E 00")
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m.read_protect_status() is False
