from unittest.mock import MagicMock
import pytest
from mks_servo.driver import MKSServo42D
from mks_servo.constants import Direction


@pytest.fixture
def fake_serial(mocker):
    fake = MagicMock()
    fake.in_waiting = 0
    mocker.patch("mks_servo.driver.serial.Serial", return_value=fake)
    return fake


def _resp(addr: int, code: int, payload: bytes) -> bytes:
    body = bytes([0xFB, addr, code]) + payload
    return body + bytes([sum(body) & 0xFF])


def test_emergency_stop(fake_serial):
    fake_serial.read.return_value = _resp(1, 0xF7, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.emergency_stop() is True
    sent = fake_serial.write.call_args[0][0]
    assert sent[:3] == bytes.fromhex("FA 01 F7")


def test_move_speed_320rpm_cw_acc2(fake_serial):
    """Manual §7.4: 'FA 01 F6 01 40 02' for dir=CW, speed=320, acc=2."""
    fake_serial.read.return_value = _resp(1, 0xF6, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.move_speed(rpm=320, acc=2, direction=Direction.CW) is True
    sent = fake_serial.write.call_args[0][0]
    assert sent == bytes.fromhex("FA 01 F6 01 40 02 34")


def test_move_speed_ccw_negative_dir_bit(fake_serial):
    fake_serial.read.return_value = _resp(1, 0xF6, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        m.move_speed(rpm=320, acc=2, direction=Direction.CCW)
    sent = fake_serial.write.call_args[0][0]
    assert sent == bytes.fromhex("FA 01 F6 81 40 02 B4")


def test_move_speed_clamps_rpm(fake_serial):
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        with pytest.raises(ValueError):
            m.move_speed(rpm=4000, acc=2, direction=Direction.CW)


def test_save_speed_mode_state_save(fake_serial):
    fake_serial.read.return_value = _resp(1, 0xFF, b"\x02")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.save_speed_mode_state(save=True) is True
    sent = fake_serial.write.call_args[0][0]
    assert sent[:4] == bytes.fromhex("FA 01 FF C8")


def test_save_speed_mode_state_clean(fake_serial):
    fake_serial.read.return_value = _resp(1, 0xFF, b"\x02")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        m.save_speed_mode_state(save=False)
    sent = fake_serial.write.call_args[0][0]
    assert sent[:4] == bytes.fromhex("FA 01 FF CA")
