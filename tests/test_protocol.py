import pytest
from mks_servo.protocol import checksum8, build_frame


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
