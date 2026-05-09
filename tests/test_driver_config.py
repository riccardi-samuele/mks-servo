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


from mks_servo.constants import WorkMode


def test_set_work_mode_sends_correct_byte(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x82, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.set_work_mode(WorkMode.SR_vFOC) is True
    sent = fake_serial.write.call_args[0][0]
    assert sent[:4] == bytes.fromhex("FA 01 82 05")


def test_set_work_current_ma_encodes_uint16_be(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x83, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.set_work_current_ma(1600) is True
    sent = fake_serial.write.call_args[0][0]
    assert sent[:5] == bytes.fromhex("FA 01 83 06 40")


def test_set_work_current_ma_clamps_max(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x83, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        with pytest.raises(ValueError):
            m.set_work_current_ma(5000)


def test_set_subdivision(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x84, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.set_subdivision(64) is True
    sent = fake_serial.write.call_args[0][0]
    assert sent[:4] == bytes.fromhex("FA 01 84 40")


def test_set_subdivision_rejects_zero(fake_serial):
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        with pytest.raises(ValueError):
            m.set_subdivision(0)


def test_read_all_config_returns_dict(fake_serial):
    """Manual §5.9: read 0x47, response is FB 01 47 + 34 bytes payload + CRC."""
    payload = bytearray(34)
    payload[0] = 5    # mode = SR_vFOC
    payload[1] = 0x06; payload[2] = 0x40  # current = 1600 mA
    payload[3] = 4    # hold = 50%
    payload[4] = 0x10  # subdivision = 16
    payload[5] = 0    # En
    payload[6] = 0    # Dir = CW
    body = bytes([0xFB, 0x01, 0x47]) + bytes(payload)
    fake_serial.read.return_value = body + bytes([sum(body) & 0xFF])

    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        cfg = m.read_all_config()

    assert cfg["mode"] == 5
    assert cfg["current_ma"] == 1600
    assert cfg["subdivision"] == 16
    assert isinstance(cfg["raw"], bytes) and len(cfg["raw"]) == 34
