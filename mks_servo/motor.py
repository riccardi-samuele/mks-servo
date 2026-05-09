"""Motor: Level 0 + Level 1 high-level API. Wraps a RawDriver.

Level 0 surface (Servo-style):
    attach / detach / write / read / error / is_moving / emergency_stop

Level 1 surface (this file, added incrementally by Tasks 11-24):
    properties: work_current_ma, hold_current_pct, microsteps, mode, direction,
                position_limits, speed_limit_rpm
    methods:    set_origin, move_relative, enable, disable, wait_until_idle,
                calibrate, restart, restore_defaults

Higher methods/properties are added in subsequent tasks of the v0.1.0 plan;
this Task 11 only adds the skeleton: constructor, attach, detach, context
manager, and the `model` read-only convenience property.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

_logger = logging.getLogger("mks_servo.motor")

from mks_servo.exceptions import LimitExceeded, MotorNotAttached
from mks_servo.profile import Profile
from mks_servo.raw import RawDriver

ENCODER_COUNTS_PER_REV = 0x4000  # 16384


def _counts_to_angle(counts: int, gear_ratio: float, origin_offset: int) -> float:
    """Inverse of `_angle_to_counts`."""
    motor_counts = counts - origin_offset
    motor_deg = motor_counts * 360.0 / ENCODER_COUNTS_PER_REV
    return motor_deg / gear_ratio


# The firmware reports angle error in driver units: 51200 = 360°.
_ANGLE_ERROR_UNITS_PER_REV = 51200


def _angle_to_counts(angle_deg: float, gear_ratio: float, origin_offset: int) -> int:
    """Convert output-axis angle (degrees) to encoder counts (motor side).

    output_deg → motor_deg = output_deg * gear_ratio
    motor_deg → counts = motor_deg / 360 * 16384
    Apply origin_offset (subtracted: zero in counts is at origin_offset).
    """
    motor_deg = angle_deg * gear_ratio
    counts = round(motor_deg / 360.0 * ENCODER_COUNTS_PER_REV)
    return counts - origin_offset


def _apply_speed_policy(rpm: int,
                        max_rpm: Optional[int],
                        policy: str) -> int:
    if max_rpm is None or rpm <= max_rpm:
        return rpm
    if policy == "reject":
        raise LimitExceeded(kind="speed", value=rpm, limit=max_rpm)
    if policy == "clamp":
        return max_rpm
    if policy == "warn":
        _logger.warning("speed limit exceeded: %d > %d (proceeding)", rpm, max_rpm)
        return rpm
    raise LimitExceeded(kind="speed", value=rpm, limit=max_rpm,
                        message=f"unknown on_violation policy: {policy!r}")


def _apply_position_policy(angle_deg: float,
                           min_deg: Optional[float],
                           max_deg: Optional[float],
                           policy: str) -> float:
    if min_deg is None or max_deg is None:
        return angle_deg
    if min_deg <= angle_deg <= max_deg:
        return angle_deg
    limit = max_deg if angle_deg > max_deg else min_deg
    if policy == "reject":
        raise LimitExceeded(kind="position", value=angle_deg, limit=limit)
    if policy == "clamp":
        return max(min_deg, min(max_deg, angle_deg))
    if policy == "warn":
        _logger.warning(
            "position limit exceeded: %.3f outside [%.3f, %.3f] (proceeding)",
            angle_deg, min_deg, max_deg,
        )
        return angle_deg
    raise LimitExceeded(kind="position", value=angle_deg, limit=limit,
                        message=f"unknown on_violation policy: {policy!r}")


class Motor:
    """High-level interface to a single MKS SERVO motor.

    Lifecycle:
        m = Motor.from_profile("wrist")
        m.attach()                # opens transport, applies profile.config
        m.write(45)               # (added in Task 12)
        m.detach()                # closes transport, disables motor

    Or as a context manager:
        with Motor.from_profile("wrist") as m:
            m.write(45)
    """

    def __init__(self, profile: Profile, *, raw: Optional[RawDriver] = None):
        self.profile = profile
        self._raw: Optional[RawDriver] = raw
        self._owns_raw: bool = raw is None
        self._attached: bool = False
        # Runtime overrides (in-memory; not persisted to profile).
        self._position_limits: tuple[Optional[float], Optional[float]] = (
            profile.limits.position.min_deg, profile.limits.position.max_deg)
        self._speed_limit_rpm: Optional[int] = profile.limits.speed.max_rpm_safe

    # ─── Constructors ──────────────────────────────────────────────────
    @classmethod
    def from_profile(cls,
                     profile: Union[str, Path, Profile],
                     *,
                     port: Optional[str] = None) -> "Motor":
        """Construct a Motor from a Profile, a path, or a name (uses Profile.load)."""
        if isinstance(profile, Profile):
            prof = profile
        else:
            prof = Profile.load(str(profile))

        prof.validate()

        if port is not None:
            prof.transport.port = port

        return cls(prof, raw=None)

    # ─── Lifecycle ─────────────────────────────────────────────────────
    def attach(self) -> None:
        """Open the serial transport (if owned), apply profile.config to the driver.

        Idempotent: a second call after a successful attach is a no-op.
        """
        if self._attached:
            return
        if self._raw is None:
            tr = self.profile.transport
            if not tr.port:
                raise RuntimeError(
                    "no transport.port: set it in the profile or pass `port=` "
                    "to Motor.from_profile()"
                )
            self._raw = RawDriver(
                port=tr.port, baud=tr.baud,
                addr=self.profile.driver.slave_addr,
                timeout=tr.timeout_s,
            )
        self._apply_profile_config()
        self._attached = True

    def detach(self) -> None:
        """Disable motor, close transport (if owned). Idempotent."""
        if not self._attached:
            return
        try:
            if self._raw is not None:
                self._raw.enable(False)
        finally:
            if self._owns_raw and self._raw is not None:
                close = getattr(self._raw, "close", None)
                if callable(close):
                    close()
                self._raw = None
            self._attached = False

    def __enter__(self) -> "Motor":
        self.attach()
        return self

    def __exit__(self, *_) -> None:
        self.detach()

    # ─── Internals ─────────────────────────────────────────────────────
    def _apply_profile_config(self) -> None:
        c = self.profile.config
        self._raw.set_work_mode(c.mode)
        self._raw.set_subdivision(c.microsteps)
        self._raw.set_work_current_ma(c.work_current_ma)

    def _require_attached(self) -> None:
        if not self._attached:
            raise MotorNotAttached(
                "call attach() before using the motor (or use a `with` block)"
            )

    # ─── Level 0 motion ───────────────────────────────────────────────
    def write(self, angle_deg: float, *,
              rpm: Optional[int] = None,
              acc: Optional[int] = None,
              blocking: bool = True,
              timeout: Optional[float] = None) -> None:
        """Move to absolute angle (output-axis degrees).

        Limit enforcement is added in Tasks 14-16; this Task 12 implementation
        is the bare conversion + raw call + optional blocking wait.

        Args:
            angle_deg: target angle in output-axis degrees (gear_ratio applied).
            rpm: speed in revolutions per minute. Default 300.
            acc: acceleration setpoint (1..255). Default 50.
            blocking: if True, wait_until_idle is called before returning.
            timeout: forwarded to wait_until_idle(timeout=...) when blocking.

        Raises:
            MotorNotAttached: if attach() has not been called.
        """
        self._require_attached()

        # Use runtime overrides (set via the position_limits property in Task 19);
        # fall back to profile values otherwise. In Task 11 the constructor
        # initialised _position_limits from the profile, so this is the same
        # source unless overridden later.
        pos_min, pos_max = self._position_limits
        angle_deg = _apply_position_policy(
            angle_deg, pos_min, pos_max,
            self.profile.limits.position.on_violation,
        )

        eff_rpm = 300 if rpm is None else int(rpm)
        eff_rpm = _apply_speed_policy(
            eff_rpm, self._speed_limit_rpm,
            self.profile.limits.speed.on_violation,
        )
        eff_acc = 50 if acc is None else int(acc)
        counts = _angle_to_counts(
            angle_deg,
            self.profile.mechanical.gear_ratio,
            self.profile.origin.encoder_offset_counts,
        )
        self._raw.move_absolute_axis(counts, eff_rpm, eff_acc)
        if blocking:
            self._raw.wait_until_idle(timeout=timeout)

    def read(self) -> float:
        """Current absolute angle in output-axis degrees (gear_ratio + origin applied)."""
        self._require_attached()
        counts = self._raw.read_encoder_addition()
        return _counts_to_angle(counts,
                                self.profile.mechanical.gear_ratio,
                                self.profile.origin.encoder_offset_counts)

    def error(self) -> float:
        """Current following error (encoder vs commanded), in output-axis degrees.

        The firmware reports angle error in driver units where 51200 = 360°.
        """
        self._require_attached()
        units = self._raw.read_angle_error()
        motor_deg = units * 360.0 / _ANGLE_ERROR_UNITS_PER_REV
        return motor_deg / self.profile.mechanical.gear_ratio

    def is_moving(self) -> bool:
        """True if the motor is currently executing a move."""
        self._require_attached()
        from mks_servo.raw import MotorStatus
        _MOVING = {
            MotorStatus.SPEED_UP,
            MotorStatus.SPEED_DOWN,
            MotorStatus.FULL_SPEED,
            MotorStatus.HOMING,
            MotorStatus.CALIBRATING,
        }
        return self._raw.read_motor_status() in _MOVING

    def emergency_stop(self) -> None:
        """Best-effort immediate stop. Never raises.

        Safe to call from signal handlers or before attach().
        """
        if self._raw is None:
            return
        try:
            self._raw.emergency_stop()
        except Exception:
            pass
        try:
            self._raw.enable(False)
        except Exception:
            pass

    # ─── Read-only convenience ─────────────────────────────────────────
    @property
    def model(self) -> str:
        return self.profile.driver.model

    # ─── Level 1 properties ───────────────────────────────────────────
    @property
    def work_current_ma(self) -> int:
        """Operating current in milliamps. Setter writes to driver immediately
        and validates against `profile.limits.current.max_ma` (always reject)."""
        return self.profile.config.work_current_ma

    @work_current_ma.setter
    def work_current_ma(self, value: int) -> None:
        self._require_attached()
        value = int(value)
        max_ma = self.profile.limits.current.max_ma
        if value > max_ma:
            raise LimitExceeded(kind="current", value=value, limit=max_ma)
        if value < 0:
            raise LimitExceeded(kind="current", value=value, limit=0,
                                message=f"current must be >= 0, got {value}")
        self._raw.set_work_current_ma(value)
        self.profile.config.work_current_ma = value
