def checksum8(buf: bytes) -> int:
    """8-bit modular sum (manual §4)."""
    return sum(buf) & 0xFF
