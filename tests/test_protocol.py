import pytest
from mks_servo.protocol import checksum8


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
