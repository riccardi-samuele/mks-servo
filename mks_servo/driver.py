import serial
from enum import IntEnum

from . import protocol
from .constants import OpCode, ENCODER_COUNTS_PER_REV, NEMA17_FULL_STEPS


class MotorStatus(IntEnum):
    QUERY_FAIL = 0
    STOPPED = 1
    SPEED_UP = 2
    SPEED_DOWN = 3
    FULL_SPEED = 4
    HOMING = 5
    CALIBRATING = 6


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

    def read_speed_rpm(self) -> int:
        """Cmd 0x32: signed RPM (>0 = CCW, <0 = CW)."""
        payload = self._txn(OpCode.READ_SPEED_RPM, expect_payload_len=2)
        return int.from_bytes(payload, "big", signed=True)

    def read_pulses(self) -> int:
        """Cmd 0x33: pulses received (int32 BE)."""
        payload = self._txn(OpCode.READ_PULSES, expect_payload_len=4)
        return int.from_bytes(payload, "big", signed=True)

    def read_angle_error(self) -> int:
        """Cmd 0x39: angle error in driver units (51200 = 360°)."""
        payload = self._txn(OpCode.READ_ANGLE_ERROR, expect_payload_len=4)
        return int.from_bytes(payload, "big", signed=True)

    def read_motor_status(self) -> MotorStatus:
        """Cmd 0xF1: motor running status."""
        payload = self._txn(OpCode.QUERY_STATUS, expect_payload_len=1)
        return MotorStatus(payload[0])

    def read_angle_degrees(self) -> float:
        """Cumulative angle in degrees, from encoder addition."""
        return encoder_counts_to_degrees(self.read_encoder_addition())

    def calibrate(self) -> None:
        """Cmd 0x80: calibrate the encoder. Motor MUST be unloaded.
        Raises CalibrationFailed on status=2.
        """
        from .exceptions import CalibrationFailed
        payload = self._txn(OpCode.CALIBRATE, b"\x00", expect_payload_len=1)
        if payload == b"\x02":
            raise CalibrationFailed("driver returned status=2 (calibration fail)")

    def restart(self) -> bool:
        payload = self._txn(OpCode.RESTART, expect_payload_len=1)
        return payload == b"\x01"

    def restore_defaults(self) -> bool:
        """Wipes calibration and config. Requires re-calibration after."""
        payload = self._txn(OpCode.RESTORE_DEFAULTS, expect_payload_len=1)
        return payload == b"\x01"

    def set_zero_point(self) -> bool:
        """Cmd 0x92: set the current axis to 0 ('go-home without movement')."""
        payload = self._txn(OpCode.SET_ZERO_POINT, expect_payload_len=1)
        return payload == b"\x01"

    def release_protection(self) -> bool:
        """Cmd 0x3D: clear stall-protection latch."""
        payload = self._txn(OpCode.RELEASE_PROTECTION, expect_payload_len=1)
        return payload == b"\x01"

    def set_work_mode(self, mode) -> bool:
        """Cmd 0x82: set work mode."""
        payload = self._txn(OpCode.SET_WORK_MODE, bytes([int(mode)]), expect_payload_len=1)
        return payload == b"\x01"

    def set_work_current_ma(self, current_ma: int) -> bool:
        """Cmd 0x83: working current in mA. SERVO42D max = 3000, must be > 0."""
        if not 0 < current_ma <= 3000:
            raise ValueError(f"current_ma must be 1..3000 (SERVO42D), got {current_ma}")
        data = current_ma.to_bytes(2, "big", signed=False)
        payload = self._txn(OpCode.SET_WORK_CURRENT, data, expect_payload_len=1)
        return payload == b"\x01"

    def set_subdivision(self, microsteps: int) -> bool:
        """Cmd 0x84: microsteps. 1..256 (256 sent as 0x00 by manual convention)."""
        if not 1 <= microsteps <= 256:
            raise ValueError(f"microsteps must be 1..256, got {microsteps}")
        byte_val = 0x00 if microsteps == 256 else microsteps
        payload = self._txn(OpCode.SET_SUBDIVISION, bytes([byte_val]), expect_payload_len=1)
        return payload == b"\x01"


def degrees_to_encoder_counts(deg: float) -> int:
    return int(round(deg * ENCODER_COUNTS_PER_REV / 360))


def encoder_counts_to_degrees(counts: int) -> float:
    return counts * 360.0 / ENCODER_COUNTS_PER_REV


def degrees_to_pulses(deg: float, microsteps: int = 16) -> int:
    return int(round(deg * NEMA17_FULL_STEPS * microsteps / 360))
