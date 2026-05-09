from .constants import HEAD_DOWN


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
