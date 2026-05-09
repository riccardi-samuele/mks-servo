from unittest.mock import MagicMock
import pytest
from mks_servo.driver import MKSServo42D
from mks_servo.exceptions import CalibrationFailed


@pytest.fixture
def fake_serial(mocker):
    fake = MagicMock()
    fake.in_waiting = 0
    mocker.patch("mks_servo.driver.serial.Serial", return_value=fake)
    return fake


def _resp(addr: int, code: int, payload: bytes) -> bytes:
    body = bytes([0xFB, addr, code]) + payload
    return body + bytes([sum(body) & 0xFF])


def test_calibrate_success(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x80, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        m.calibrate()


def test_calibrate_fail_raises(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x80, b"\x02")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        with pytest.raises(CalibrationFailed):
            m.calibrate()


def test_restart_sends_correct_frame(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x41, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        m.restart()
    sent = fake_serial.write.call_args[0][0]
    assert sent[:3] == bytes.fromhex("FA 01 41")


def test_restore_defaults(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x3F, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.restore_defaults() is True


def test_set_zero_point(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x92, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.set_zero_point() is True


def test_release_protection(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x3D, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.release_protection() is True
