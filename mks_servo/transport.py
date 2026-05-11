"""Serial I/O wrapper. Owns retry, timeout, framing-level error mapping."""
from __future__ import annotations

import threading
import time
from typing import Tuple

import serial

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


class SharedTransport:
    """A serial transport shared by multiple RawDrivers on the same bus.

    Wraps a serial.Serial + a threading.Lock so transactions from different
    drivers serialise correctly on the half-duplex RS485 bus.
    """

    def __init__(self, port: str, baud: int = 38400, timeout: float = 3.0):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self._ser: serial.Serial | None = None
        self._lock = threading.Lock()

    def open(self) -> None:
        if self._ser is not None:
            return
        self._ser = serial.Serial(
            port=self.port,
            baudrate=self.baud,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=self.timeout,
        )

    def close(self) -> None:
        if self._ser is None:
            return
        self._ser.close()
        self._ser = None

    def __enter__(self) -> "SharedTransport":
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def transact(self, *, addr: int, code: int, data: bytes,
                 expect_payload_len: int,
                 timeout: float | None = None):
        """Locked transact. Forwards to the module-level transact() function."""
        if self._ser is None:
            raise RuntimeError(
                "transport not open; call .open() or use as context manager"
            )
        with self._lock:
            return transact(
                self._ser, addr=addr, code=code, data=data,
                expect_payload_len=expect_payload_len,
                timeout=timeout if timeout is not None else self.timeout,
            )
