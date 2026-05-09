import time

from .constants import HEAD_DOWN, HEAD_UP
from .exceptions import ChecksumError, CommTimeout, ProtocolError


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


def transact(
    ser,
    addr: int,
    code: int,
    data: bytes = b"",
    expect_payload_len: int | None = None,
    timeout: float = 0.5,
) -> bytes:
    """Send a frame and read back the matching uplink frame.

    Returns the payload (bytes between code and checksum).
    Raises CommTimeout if no full frame arrives within timeout.
    """
    request = build_frame(addr, code, data)
    ser.reset_input_buffer() if hasattr(ser, "reset_input_buffer") else None
    ser.write(request)
    if hasattr(ser, "flush"):
        ser.flush()

    if expect_payload_len is None:
        # Best effort: read whatever is available; the caller knows the layout.
        # Default to 8-byte read with timeout.
        expect_payload_len = 5
    expected_total = 4 + expect_payload_len  # head+addr+code+payload+crc

    deadline = time.monotonic() + timeout
    buf = bytearray()
    while len(buf) < expected_total:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise CommTimeout(
                f"only {len(buf)}/{expected_total} bytes received before {timeout}s timeout"
            )
        ser.timeout = remaining
        chunk = ser.read(expected_total - len(buf))
        if not chunk:
            raise CommTimeout(
                f"only {len(buf)}/{expected_total} bytes received before {timeout}s timeout"
            )
        buf.extend(chunk)

    try:
        _, _, payload = parse_frame(bytes(buf))
    except (ChecksumError, ProtocolError) as exc:
        raise CommTimeout(f"received {len(buf)} bytes but frame is invalid: {exc}") from exc
    return payload
