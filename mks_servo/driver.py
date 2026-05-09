import serial

from . import protocol
from .constants import OpCode


class MKSServo42D:
    def __init__(self, port: str, baud: int = 38400, addr: int = 1, timeout: float = 0.5) -> None:
        self.port = port
        self.baud = baud
        self.addr = addr
        self.timeout = timeout
        self._ser: serial.Serial | None = None
        self._enabled = False

    def open(self) -> None:
        self._ser = serial.Serial(
            port=self.port,
            baudrate=self.baud,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=self.timeout,
        )

    def close(self) -> None:
        if self._enabled:
            try:
                self.enable(False)
            except Exception:
                pass
            self._enabled = False
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def __enter__(self) -> "MKSServo42D":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # Internal helper used by all command methods
    def _txn(self, code: int, data: bytes = b"", expect_payload_len: int | None = None) -> bytes:
        if self._ser is None:
            raise RuntimeError("serial not open; call .open() or use as context manager")
        return protocol.transact(
            self._ser, addr=self.addr, code=code, data=data,
            expect_payload_len=expect_payload_len, timeout=self.timeout,
        )

    def enable(self, on: bool) -> bool:
        """Enable (True) or disable (False) the motor (cmd 0xF3). Returns True on success."""
        payload = self._txn(OpCode.ENABLE, bytes([0x01 if on else 0x00]), expect_payload_len=1)
        ok = payload == b"\x01"
        if ok:
            self._enabled = on
        return ok

    def read_encoder(self) -> tuple[int, int]:
        """Cmd 0x30: returns (carry int32 BE, value uint16 BE in 0..0x3FFF)."""
        payload = self._txn(OpCode.READ_ENCODER, expect_payload_len=6)
        carry = int.from_bytes(payload[0:4], "big", signed=True)
        value = int.from_bytes(payload[4:6], "big", signed=False)
        return carry, value

    def read_encoder_addition(self) -> int:
        """Cmd 0x31: cumulative encoder value (int48 BE). 0x4000 per CW turn."""
        payload = self._txn(OpCode.READ_ENCODER_ADDITION, expect_payload_len=6)
        return int.from_bytes(payload, "big", signed=True)
