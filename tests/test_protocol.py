import pytest
from mks_servo.protocol import checksum8, build_frame, parse_frame
from mks_servo.exceptions import ChecksumError, ProtocolError


def test_checksum_manual_example_calibrate():
    """Manual §4: 'FA 01 80 00 CRC' -> CRC = 0x7B."""
    assert checksum8(bytes.fromhex("FA 01 80 00")) == 0x7B


def test_checksum_manual_example_read_encoder():
    """Manual §7.3: 'FA 01 30 2B' -> CRC = 0x2B."""
    assert checksum8(bytes.fromhex("FA 01 30")) == 0x2B


def test_checksum_empty():
    assert checksum8(b"") == 0


def test_checksum_overflow_wraps_to_byte():
    # 0xFF + 0xFF = 0x1FE; & 0xFF = 0xFE
    assert checksum8(bytes([0xFF, 0xFF])) == 0xFE


def test_build_frame_calibrate():
    """Manual §4 example: 'FA 01 80 00 7B'."""
    assert build_frame(addr=0x01, code=0x80, data=b"\x00") == bytes.fromhex("FA 01 80 00 7B")


def test_build_frame_no_data():
    """Read encoder, no data: FA 01 30 2B."""
    assert build_frame(addr=0x01, code=0x30) == bytes.fromhex("FA 01 30 2B")


def test_build_frame_speed_mode():
    """Manual §7.4: 'FA 01 F6 01 40 02 34' (dir=CW, speed=320, acc=2)."""
    assert build_frame(0x01, 0xF6, b"\x01\x40\x02") == bytes.fromhex("FA 01 F6 01 40 02 34")


def test_build_frame_rejects_addr_out_of_range():
    with pytest.raises(ValueError):
        build_frame(addr=256, code=0x30)


def test_build_frame_rejects_code_out_of_range():
    with pytest.raises(ValueError):
        build_frame(addr=1, code=300)


def test_parse_frame_encoder_response():
    """Manual §7.3: 'FB 01 30 FF FF FF FF 22 69 B3'."""
    addr, code, payload = parse_frame(bytes.fromhex("FB 01 30 FF FF FF FF 22 69 B3"))
    assert addr == 0x01
    assert code == 0x30
    assert payload == bytes.fromhex("FF FF FF FF 22 69")


def test_parse_frame_status_only():
    """Calibrate response: 'FB 01 80 01 7D'."""
    addr, code, payload = parse_frame(bytes.fromhex("FB 01 80 01 7D"))
    assert (addr, code, payload) == (0x01, 0x80, b"\x01")


def test_parse_frame_bad_checksum():
    bad = bytes.fromhex("FB 01 80 01 00")  # last byte should be 0x7D
    with pytest.raises(ChecksumError):
        parse_frame(bad)


def test_parse_frame_bad_header():
    with pytest.raises(ProtocolError):
        parse_frame(bytes.fromhex("AA 01 80 01 00"))


def test_parse_frame_too_short():
    with pytest.raises(ProtocolError):
        parse_frame(bytes.fromhex("FB 01"))


from unittest.mock import MagicMock
from mks_servo.transport import transact
from mks_servo.exceptions import CommTimeout


def _fake_serial(reply: bytes):
    ser = MagicMock()
    ser.read.return_value = reply
    ser.in_waiting = len(reply)
    return ser


def test_transact_round_trip():
    ser = _fake_serial(bytes.fromhex("FB 01 80 01 7D"))
    addr, code, payload = transact(ser, addr=1, code=0x80, data=b"\x00", expect_payload_len=1, timeout=0.1)
    assert addr == 1
    assert code == 0x80
    assert payload == b"\x01"
    sent = ser.write.call_args[0][0]
    assert sent == bytes.fromhex("FA 01 80 00 7B")


def test_transact_timeout():
    ser = _fake_serial(b"")  # no reply
    with pytest.raises(CommTimeout):
        transact(ser, addr=1, code=0x30, expect_payload_len=6, timeout=0.05)


def test_transact_truncated_response():
    ser = _fake_serial(bytes.fromhex("FB 01"))  # only 2 bytes
    with pytest.raises(CommTimeout):
        transact(ser, addr=1, code=0x80, data=b"\x00", expect_payload_len=1, timeout=0.05)
