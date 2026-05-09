"""Serial I/O wrapper. Owns retry, timeout, framing-level error mapping."""
from __future__ import annotations

import time
from typing import Tuple

from mks_servo.protocol import build_frame, parse_frame
from mks_servo.exceptions import CommTimeout, ChecksumError, ProtocolError


def transact(
    ser,
    addr: int,
    code: int,
    data: bytes = b"",
    expect_payload_len: int | None = None,
    timeout: float = 0.5,
) -> Tuple[int, int, bytes]:
    """Send a frame and read back the matching uplink frame.

    Returns a tuple of (addr, code, payload).
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
                f"got {len(buf)}/{expected_total} bytes within {timeout}s"
            )
        ser.timeout = remaining
        chunk = ser.read(expected_total - len(buf))
        if not chunk:
            raise CommTimeout(
                f"got {len(buf)}/{expected_total} bytes within {timeout}s"
            )
        buf.extend(chunk)

    try:
        addr_resp, code_resp, payload = parse_frame(bytes(buf))
    except (ChecksumError, ProtocolError) as exc:
        raise CommTimeout(f"received {len(buf)} bytes but frame is invalid: {exc}") from exc
    return addr_resp, code_resp, payload
