"""Direct mapping of MKS SERVO42D RS485 opcodes to Python methods.

`RawDriver` is the low-level driver: each public method corresponds to a
single firmware command (ping, set_work_mode, move_absolute_axis, …) with no
profile awareness, no software limits, no unit conversions beyond what the
firmware itself encodes. Higher-level use cases should go through the `Motor`
class (added in later v0.1.0 tasks); this module is kept available for
power-users who need protocol-level access.
"""
import serial
import time
from enum import IntEnum

from .transport import transact, SharedTransport
from .constants import Direction, OpCode, ENCODER_COUNTS_PER_REV, NEMA17_FULL_STEPS


class MotorStatus(IntEnum):
    QUERY_FAIL = 0
    STOPPED = 1
    SPEED_UP = 2
    SPEED_DOWN = 3
    FULL_SPEED = 4
    HOMING = 5
    CALIBRATING = 6


class RawDriver:
    """1:1 wrapper around the MKS SERVO42D firmware command set (V1.0.6 manual).

    Opens a serial transport in `__init__`, exposes one public method per opcode.
    Not aware of profiles or user-space limits — that lives in `Motor`.
    """

    def __init__(self, port: str | None = None, baud: int = 38400,
                 addr: int = 1, timeout: float = 0.5,
                 *,
                 transport: "SharedTransport | None" = None) -> None:
        self.port = port
        self.baud = baud
        self.addr = addr
        self.timeout = timeout
        # External transport: bus owns lifecycle.
        # Internal transport: created lazily in open() based on port/baud/timeout.
        self._transport: SharedTransport | None = transport
        self._owns_transport = transport is None
        self._ser: serial.Serial | None = None
        self._enabled = False
        # If an external transport was given AND it's already open, expose its serial.
        if transport is not None:
            self._ser = getattr(transport, "_ser", None)

    def open(self) -> None:
        if not self._owns_transport:
            # External transport: bus owns it. Just refresh the local _ser cache.
            if self._transport is not None:
                self._ser = self._transport._ser
            return
        if self._transport is None:
            self._transport = SharedTransport(
                port=self.port, baud=self.baud, timeout=self.timeout,
            )
        self._transport.open()
        self._ser = self._transport._ser

    def close(self) -> None:
        if self._enabled:
            try:
                self.enable(False)
            except Exception:
                pass
            self._enabled = False
        if self._owns_transport and self._transport is not None:
            self._transport.close()
            self._transport = None
        self._ser = None

    def __enter__(self) -> "RawDriver":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # Internal helper used by all command methods
    def _txn(self, code: int, data: bytes = b"", expect_payload_len: int | None = None) -> bytes:
        if self._transport is None or self._transport._ser is None:
            raise RuntimeError(
                "transport not open; call .open() or use as context manager"
            )
        _, _, payload = self._transport.transact(
            addr=self.addr, code=code, data=data,
            expect_payload_len=expect_payload_len, timeout=self.timeout,
        )
        return payload

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

    def read_protect_status(self) -> bool:
        """Cmd 0x3E: True if motor stall protection is latched."""
        payload = self._txn(OpCode.READ_PROTECT_STATUS, expect_payload_len=1)
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

    def set_direction(self, direction: Direction) -> bool:
        """Cmd 0x85: motor rotation direction. CW=0, CCW=1."""
        payload = self._txn(
            OpCode.SET_DIRECTION, bytes([int(direction)]), expect_payload_len=1
        )
        return payload == b"\x01"

    def set_hold_current_pct(self, pct: int) -> bool:
        """Cmd 0x86: holding current as a percentage (10..90, step 10).

        The firmware encodes hold current as an index 0..8 mapping to 10..90 %.
        This method accepts the percent directly (10, 20, …, 90) and translates
        internally: idx = (pct - 10) // 10.
        """
        if not (10 <= pct <= 90) or pct % 10 != 0:
            raise ValueError(f"hold current must be 10..90 step 10, got {pct}")
        idx = (pct - 10) // 10
        payload = self._txn(
            OpCode.SET_HOLDING_CURRENT, bytes([idx]), expect_payload_len=1
        )
        return payload == b"\x01"

    def read_all_config(self) -> dict:
        """Cmd 0x47: read 38-byte config snapshot.
        Returns a dict with parsed common fields plus raw bytes for full diff.
        """
        payload = self._txn(OpCode.READ_ALL_CONFIG, expect_payload_len=34)
        return {
            "mode": payload[0],
            "current_ma": int.from_bytes(payload[1:3], "big"),
            "hold_current_pct_idx": payload[3],
            "subdivision": 256 if payload[4] == 0 else payload[4],
            "en_active": payload[5],
            "dir_cw": payload[6] == 0,
            "auto_screen_off": bool(payload[7]),
            "stall_protect": bool(payload[8]),
            "interp_enabled": bool(payload[9]),
            "baud_code": payload[10],
            "slave_addr": payload[11],
            "raw": bytes(payload),
        }

    def emergency_stop(self) -> bool:
        """Cmd 0xF7: stop everything immediately. Above 1000 RPM use stop_speed_mode instead."""
        payload = self._txn(OpCode.EMERGENCY_STOP, expect_payload_len=1)
        return payload == b"\x01"

    def move_speed(self, rpm: int, acc: int = 2, direction=None) -> bool:
        """Cmd 0xF6: continuous speed mode."""
        from .constants import Direction as _Dir
        if direction is None:
            direction = _Dir.CW
        if not 0 <= rpm <= 3000:
            raise ValueError(f"rpm must be 0..3000, got {rpm}")
        if not 0 <= acc <= 255:
            raise ValueError(f"acc must be 0..255, got {acc}")
        dir_bit = 0x80 if direction == _Dir.CCW else 0x00
        b4 = dir_bit | ((rpm >> 8) & 0x0F)
        b5 = rpm & 0xFF
        payload = self._txn(OpCode.MOVE_SPEED, bytes([b4, b5, acc]), expect_payload_len=1)
        return payload == b"\x01"

    def save_speed_mode_state(self, save: bool = True) -> bool:
        """Cmd 0xFF: save (0xC8) or clean (0xCA) speed-mode params."""
        state = 0xC8 if save else 0xCA
        payload = self._txn(OpCode.SAVE_SPEED_STATE, bytes([state]), expect_payload_len=1)
        return payload == b"\x02"

    def move_relative_pulses(self, pulses: int, rpm: int, acc: int = 2, direction=None) -> bool:
        """Cmd 0xFD: relative move by pulse count."""
        from .constants import Direction as _Dir
        if direction is None:
            direction = _Dir.CW
        if not 0 <= pulses <= 0xFFFFFFFF:
            raise ValueError(f"pulses must be 0..2^32-1, got {pulses}")
        if not 0 <= rpm <= 3000:
            raise ValueError(f"rpm must be 0..3000, got {rpm}")
        if not 0 <= acc <= 255:
            raise ValueError(f"acc must be 0..255, got {acc}")
        dir_bit = 0x80 if direction == _Dir.CCW else 0x00
        b4 = dir_bit | ((rpm >> 8) & 0x0F)
        b5 = rpm & 0xFF
        data = bytes([b4, b5, acc]) + pulses.to_bytes(4, "big", signed=False)
        payload = self._txn(OpCode.MOVE_REL_PULSES, data, expect_payload_len=1)
        return payload == b"\x01"

    def move_absolute_pulses(self, pulses: int, rpm: int, acc: int = 2) -> bool:
        """Cmd 0xFE: absolute move to a signed pulse coordinate (int32 BE)."""
        if not -(2**31) <= pulses <= 2**31 - 1:
            raise ValueError(f"pulses out of int32 range: {pulses}")
        if not 0 <= rpm <= 3000:
            raise ValueError(f"rpm must be 0..3000, got {rpm}")
        if not 0 <= acc <= 255:
            raise ValueError(f"acc must be 0..255, got {acc}")
        speed_bytes = rpm.to_bytes(2, "big", signed=False)
        data = speed_bytes + bytes([acc]) + pulses.to_bytes(4, "big", signed=True)
        payload = self._txn(OpCode.MOVE_ABS_PULSES, data, expect_payload_len=1)
        return payload == b"\x01"

    def move_relative_axis(self, counts: int, rpm: int, acc: int = 2) -> bool:
        """Cmd 0xF4: relative move by encoder counts (int32 BE). 0x4000 = 1 turn."""
        if not -(2**31) <= counts <= 2**31 - 1:
            raise ValueError(f"counts out of int32 range: {counts}")
        if not 0 <= rpm <= 3000:
            raise ValueError(f"rpm must be 0..3000, got {rpm}")
        if not 0 <= acc <= 255:
            raise ValueError(f"acc must be 0..255, got {acc}")
        data = rpm.to_bytes(2, "big") + bytes([acc]) + counts.to_bytes(4, "big", signed=True)
        payload = self._txn(OpCode.MOVE_REL_AXIS, data, expect_payload_len=1)
        return payload == b"\x01"

    def move_absolute_axis(self, counts: int, rpm: int, acc: int = 2) -> bool:
        """Cmd 0xF5: absolute move to encoder count (int32 BE). Supports real-time updates."""
        if not -(2**31) <= counts <= 2**31 - 1:
            raise ValueError(f"counts out of int32 range: {counts}")
        if not 0 <= rpm <= 3000:
            raise ValueError(f"rpm must be 0..3000, got {rpm}")
        if not 0 <= acc <= 255:
            raise ValueError(f"acc must be 0..255, got {acc}")
        data = rpm.to_bytes(2, "big") + bytes([acc]) + counts.to_bytes(4, "big", signed=True)
        payload = self._txn(OpCode.MOVE_ABS_AXIS, data, expect_payload_len=1)
        return payload == b"\x01"

    def wait_until_idle(self, timeout: float = 10.0, poll_interval: float = 0.05) -> None:
        """Poll cmd 0xF1 until status returns to STOPPED.
        Raises MotorFault if timeout is exceeded.
        """
        from .exceptions import MotorFault
        deadline = time.monotonic() + timeout
        while True:
            st = self.read_motor_status()
            if st == MotorStatus.STOPPED:
                return
            if time.monotonic() >= deadline:
                raise MotorFault(f"motor still {st.name} after {timeout}s")
            if poll_interval > 0:
                time.sleep(poll_interval)


def degrees_to_encoder_counts(deg: float) -> int:
    return int(round(deg * ENCODER_COUNTS_PER_REV / 360))


def encoder_counts_to_degrees(counts: int) -> float:
    return counts * 360.0 / ENCODER_COUNTS_PER_REV


def degrees_to_pulses(deg: float, microsteps: int = 16) -> int:
    return int(round(deg * NEMA17_FULL_STEPS * microsteps / 360))

