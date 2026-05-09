from .constants import HEAD_DOWN, HEAD_UP
from .exceptions import ChecksumError, ProtocolError


def checksum8(buf: bytes) -> int:
    """8-bit modular sum (manual §4)."""
    return sum(buf) & 0xFF


def build_frame(addr: int, code: int, data: bytes = b"") -> bytes:
    """Build a downlink frame: HEAD_DOWN | addr | code | data | checksum8."""
    if not 0 <= addr <= 0xFF:
        raise ValueError(f"addr must be 0..255, got {addr}")
    if not 0 <= code <= 0xFF:
        raise ValueError(f"code must be 0..255, got {code}")
    body = bytes([HEAD_DOWN, addr, code]) + data
    return body + bytes([checksum8(body)])


def parse_frame(buf: bytes) -> tuple[int, int, bytes]:
    """Parse an uplink frame. Returns (addr, code, payload)."""
    if len(buf) < 4:
        raise ProtocolError(f"frame too short: {len(buf)} bytes")
    if buf[0] != HEAD_UP:
        raise ProtocolError(f"bad uplink head: 0x{buf[0]:02X} (expected 0x{HEAD_UP:02X})")
    body, given_crc = buf[:-1], buf[-1]
    expected_crc = checksum8(body)
    if given_crc != expected_crc:
        raise ChecksumError(f"checksum mismatch: got 0x{given_crc:02X}, expected 0x{expected_crc:02X}")
    return body[1], body[2], bytes(body[3:])
