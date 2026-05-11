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
import time as _time
from pathlib import Path
from typing import Optional, Union

_logger = logging.getLogger("mks_servo.motor")

from datetime import datetime as _dt, timezone as _tz
from mks_servo.constants import WorkMode
from mks_servo.exceptions import (
    CalibrationFailed, CommTimeout, LimitExceeded, MotorNotAttached,
)
from mks_servo.profile import Profile
from mks_servo.raw import MotorStatus, RawDriver

ENCODER_COUNTS_PER_REV = 0x4000  # 16384

# HIL-validated delays (2026-05-09): firmware silently drops back-to-back cmds.
_CALIB_DELAY_S = 0.5
_CALIB_POLL_INTERVAL_S = 0.5


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

    def __init__(self, profile: Profile, *,
                 raw: Optional[RawDriver] = None,
                 auto_save: bool = False):
        self.profile = profile
        self.raw: Optional[RawDriver] = raw
        self._owns_raw: bool = raw is None
        self._attached: bool = False
        # Runtime overrides (in-memory; not persisted to profile).
        self._position_limits: tuple[Optional[float], Optional[float]] = (
            profile.limits.position.min_deg, profile.limits.position.max_deg)
        self._speed_limit_rpm: Optional[int] = profile.limits.speed.max_rpm_safe
        self._auto_save = auto_save
        self._auto_save_warned = False

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
        if self.raw is None:
            tr = self.profile.transport
            if not tr.port:
                raise RuntimeError(
                    "no transport.port: set it in the profile or pass `port=` "
                    "to Motor.from_profile()"
                )
            self.raw = RawDriver(
                port=tr.port, baud=tr.baud,
                addr=self.profile.driver.slave_addr,
                timeout=tr.timeout_s,
            )
            # Open the serial transport: RawDriver doesn't auto-open in __init__.
            self.raw.open()
        self._apply_profile_config()
        # Energise the motor by default (Servo-style "attach" semantics).
        # The user can disable explicitly via motor.enable(False) / disable().
        self.raw.enable(True)
        self._attached = True

    def detach(self) -> None:
        """Disable motor, close transport (if owned). Idempotent."""
        if not self._attached:
            return
        try:
            if self.raw is not None:
                self.raw.enable(False)
        finally:
            if self._owns_raw and self.raw is not None:
                close = getattr(self.raw, "close", None)
                if callable(close):
                    close()
                self.raw = None
            self._attached = False

    def __enter__(self) -> "Motor":
        self.attach()
        return self

    def __exit__(self, *_) -> None:
        self.detach()

    # ─── Internals ─────────────────────────────────────────────────────
    @staticmethod
    def _retry_on_comm_timeout(fn, *args, _settle_s: float = 0.3, **kwargs):
        """Call fn(*args, **kwargs); on a single CommTimeout, settle briefly and
        retry once. The MKS firmware can drop the reply to the first command(s)
        after a fresh connection (USB-serial adapter not yet settled, or the
        motor still decelerating from a previous session). One retry makes
        attach() robust without callers needing their own sleeps."""
        try:
            return fn(*args, **kwargs)
        except CommTimeout:
            _time.sleep(_settle_s)
            return fn(*args, **kwargs)

    def _apply_profile_config(self) -> None:
        c = self.profile.config
        self._retry_on_comm_timeout(self.raw.set_work_mode, c.mode)
        self._retry_on_comm_timeout(self.raw.set_subdivision, c.microsteps)
        self._retry_on_comm_timeout(self.raw.set_work_current_ma, c.work_current_ma)

    def _require_attached(self) -> None:
        if not self._attached:
            raise MotorNotAttached(
                "call attach() before using the motor (or use a `with` block)"
            )

    def _maybe_save(self) -> None:
        """If auto_save is on and profile has a path, persist the YAML.
        No-op (with one-time warning) if profile has no path."""
        if not self._auto_save:
            return
        if self.profile.path is None:
            if not self._auto_save_warned:
                _logger.warning(
                    "auto_save enabled but profile has no path "
                    "(template-loaded or in-memory) — saves are no-ops"
                )
                self._auto_save_warned = True
            return
        try:
            self.profile.save()
        except Exception as e:
            _logger.warning("auto_save failed: %s", e)

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
        self.raw.move_absolute_axis(counts, eff_rpm, eff_acc)
        if blocking:
            # RawDriver.wait_until_idle requires a numeric timeout; only pass
            # ours when the caller specified one, otherwise use raw's default.
            if timeout is None:
                self.raw.wait_until_idle()
            else:
                self.raw.wait_until_idle(timeout=timeout)

    def read(self) -> float:
        """Current absolute angle in output-axis degrees (gear_ratio + origin applied)."""
        self._require_attached()
        counts = self.raw.read_encoder_addition()
        return _counts_to_angle(counts,
                                self.profile.mechanical.gear_ratio,
                                self.profile.origin.encoder_offset_counts)

    def error(self) -> float:
        """Current following error (encoder vs commanded), in output-axis degrees.

        The firmware reports angle error in driver units where 51200 = 360°.
        """
        self._require_attached()
        units = self.raw.read_angle_error()
        motor_deg = units * 360.0 / _ANGLE_ERROR_UNITS_PER_REV
        return motor_deg / self.profile.mechanical.gear_ratio

    def is_moving(self) -> bool:
        """True if the motor is currently executing a move."""
        self._require_attached()
        _MOVING = {
            MotorStatus.SPEED_UP,
            MotorStatus.SPEED_DOWN,
            MotorStatus.FULL_SPEED,
            MotorStatus.HOMING,
            MotorStatus.CALIBRATING,
        }
        return self.raw.read_motor_status() in _MOVING

    def emergency_stop(self) -> None:
        """Best-effort immediate stop. Never raises.

        Safe to call from signal handlers or before attach().
        """
        if self.raw is None:
            return
        try:
            self.raw.emergency_stop()
        except Exception:
            pass
        try:
            self.raw.enable(False)
        except Exception:
            pass

    # ─── Read-only convenience ─────────────────────────────────────────
    @property
    def model(self) -> str:
        return self.profile.driver.model

    # ─── Level 1 methods ─────────────────────────────────────────────
    def set_origin(self, *, soft: bool = False) -> None:
        """Set the current position as the zero point.

        soft=False (default): writes to driver flash via cmd 0x92. Persists
        across power-cycle.

        soft=True: stores the current encoder counts as the in-memory
        `origin.encoder_offset_counts` in the profile. Does NOT touch the
        driver's flash. Profile is NOT auto-saved; call `profile.save()` to persist.
        """
        self._require_attached()
        if soft:
            counts = self.raw.read_encoder_addition()
            self.profile.origin.encoder_offset_counts = counts
            self.profile.origin.set_in_firmware = False
        else:
            # The MKS firmware is occasionally unresponsive immediately after
            # a motion completes (the wait_until_idle return doesn't guarantee
            # the driver is ready for the next flash-write command). A short
            # settle pause + a single retry on CommTimeout makes set_origin
            # robust in practice without requiring callers to add their own
            # sleeps.
            _time.sleep(0.2)
            try:
                self.raw.set_zero_point()
            except CommTimeout:
                _time.sleep(0.5)
                self.raw.set_zero_point()
            self.profile.origin.set_in_firmware = True
            self.profile.origin.encoder_offset_counts = 0
        self._maybe_save()

    def move_relative(self, delta_deg: float, *,
                      rpm: Optional[int] = None,
                      acc: Optional[int] = None,
                      blocking: bool = True,
                      timeout: Optional[float] = None) -> None:
        """Move by a delta in output-axis degrees. Reads current position,
        adds delta, calls write(). Inherits all limit checks from write()."""
        self._require_attached()
        current = self.read()
        self.write(current + delta_deg, rpm=rpm, acc=acc,
                   blocking=blocking, timeout=timeout)

    def enable(self, state: bool = True) -> None:
        """Enable (True) or disable (False) the motor (cmd 0xF3)."""
        self._require_attached()
        self.raw.enable(bool(state))

    def disable(self) -> None:
        """Alias for enable(False)."""
        self.enable(False)

    def wait_until_idle(self, timeout: Optional[float] = None) -> None:
        """Block until the motor reports it has stopped, or raise on timeout."""
        self._require_attached()
        if timeout is None:
            self.raw.wait_until_idle()
        else:
            self.raw.wait_until_idle(timeout=timeout)

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
        self.raw.set_work_current_ma(value)
        self.profile.config.work_current_ma = value
        self._maybe_save()

    @property
    def microsteps(self) -> int:
        """Microsteps per full step (1..256). Setter writes to driver immediately."""
        return self.profile.config.microsteps

    @microsteps.setter
    def microsteps(self, value: int) -> None:
        self._require_attached()
        value = int(value)
        if not (1 <= value <= 256):
            raise ValueError(f"microsteps must be in 1..256, got {value}")
        self.raw.set_subdivision(value)
        self.profile.config.microsteps = value
        self._maybe_save()

    @property
    def direction(self):
        """Rotation direction (CW or CCW). Setter writes to driver immediately."""
        return self.profile.config.direction

    @direction.setter
    def direction(self, value) -> None:
        self._require_attached()
        self.raw.set_direction(value)
        self.profile.config.direction = value
        self._maybe_save()

    @property
    def mode(self):
        """Driver work mode (WorkMode enum). Setter triggers an automatic restart()
        because the firmware re-reads the mode-dependent RPM cap only at boot.
        """
        return self.profile.config.mode

    @mode.setter
    def mode(self, value) -> None:
        self._require_attached()
        self.raw.set_work_mode(value)
        self.profile.config.mode = value
        self.raw.restart()
        # Firmware needs ~2s to come back online after restart (HIL finding).
        _time.sleep(2.0)
        # Re-apply the rest of the profile config so the driver state matches the
        # in-memory profile after the reset.
        self.raw.set_subdivision(self.profile.config.microsteps)
        self.raw.set_work_current_ma(self.profile.config.work_current_ma)
        self._maybe_save()

    @property
    def hold_current_pct(self) -> int:
        """Hold-current percent (10..90, step 10). Setter writes to driver immediately."""
        return self.profile.config.hold_current_pct

    @hold_current_pct.setter
    def hold_current_pct(self, value: int) -> None:
        self._require_attached()
        value = int(value)
        if not (10 <= value <= 90) or value % 10 != 0:
            raise ValueError(
                f"hold_current_pct must be 10..90 step 10, got {value}"
            )
        self.raw.set_hold_current_pct(value)
        self.profile.config.hold_current_pct = value
        self._maybe_save()

    # Read-only telemetry
    @property
    def position_counts(self) -> int:
        """Cumulative encoder counts (raw, no gear/origin applied)."""
        self._require_attached()
        return self.raw.read_encoder_addition()

    @property
    def speed_rpm(self) -> int:
        """Signed RPM (positive = CCW, negative = CW per firmware convention)."""
        self._require_attached()
        return self.raw.read_speed_rpm()

    @property
    def status(self):
        """Current MotorStatus enum value."""
        self._require_attached()
        return self.raw.read_motor_status()

    @property
    def enabled(self) -> bool:
        """True if the motor is currently enabled.

        Note: this reads the cached `_enabled` flag inside RawDriver, set by
        the last `enable(...)` call. There is no firmware-side query for this.
        """
        self._require_attached()
        return bool(getattr(self.raw, "_enabled", False))

    # Runtime limit overrides (in-memory, NOT persisted to profile)
    @property
    def position_limits(self) -> tuple:
        return self._position_limits

    @position_limits.setter
    def position_limits(self, value: tuple) -> None:
        if not isinstance(value, tuple) or len(value) != 2:
            raise ValueError("position_limits must be a 2-tuple (min, max)")
        self._position_limits = value
        self._maybe_save()

    @property
    def speed_limit_rpm(self):
        return self._speed_limit_rpm

    @speed_limit_rpm.setter
    def speed_limit_rpm(self, value) -> None:
        self._speed_limit_rpm = None if value is None else int(value)
        self._maybe_save()

    def calibrate(self, *,
                  current_ma: int = 3000,
                  timeout: float = 30.0) -> None:
        """Run the FOC calibration sequence with the empirically determined delays.

        The HIL session 2026-05-09 established that calibration only succeeds
        when the configuration is set with 500 ms between each command — back-
        to-back set_* calls are silently dropped by the firmware.

        On success: profile.characterization.last_calibrated is updated. The
        previous work_current_ma is restored. Profile is NOT auto-saved.

        On failure: the previous current is restored (best-effort) and a
        CalibrationFailed is raised.

        Args:
            current_ma: high current to use during calibration. Default 3000mA
                       (NEMA17 needs this to overcome static friction; HIL finding).
            timeout: max wall-clock seconds to wait for calibration to complete.
        """
        self._require_attached()
        previous_current = self.profile.config.work_current_ma

        try:
            self.raw.enable(False)
            _time.sleep(_CALIB_DELAY_S)
            self.raw.set_work_mode(WorkMode.SR_vFOC)
            _time.sleep(_CALIB_DELAY_S)
            self.raw.set_subdivision(16)
            _time.sleep(_CALIB_DELAY_S)
            self.raw.set_work_current_ma(int(current_ma))
            _time.sleep(_CALIB_DELAY_S)

            # Issue the calibrate opcode. RawDriver.calibrate() raises
            # CalibrationFailed on status=2; let that propagate.
            self.raw.calibrate()

            # Poll for completion (or timeout).
            deadline = _time.monotonic() + timeout
            while True:
                status = self.raw.read_motor_status()
                if status != MotorStatus.CALIBRATING:
                    break
                if _time.monotonic() > deadline:
                    raise CalibrationFailed(
                        f"timeout: calibration did not complete within {timeout}s"
                    )
                _time.sleep(_CALIB_POLL_INTERVAL_S)

            self.profile.characterization.last_calibrated = _dt.now(_tz.utc)
            self._maybe_save()
        finally:
            # Always restore previous current — best effort, swallow errors.
            try:
                self.raw.set_work_current_ma(previous_current)
            except Exception:
                pass

    def restart(self) -> None:
        """Restart the driver (cmd 0x41) and re-apply the profile config.

        The driver takes ~2s to come back online; this method blocks for that
        sleep before re-asserting profile-driven settings (work_mode,
        microsteps, work_current_ma).
        """
        self._require_attached()
        self.raw.restart()
        _time.sleep(2.0)
        self._apply_profile_config()
        self._maybe_save()

    def restore_defaults(self) -> None:
        """Reset driver to factory defaults (cmd 0x3F).

        WARNING: erases mode, current, microsteps, address, baud rate, and
        the calibration. The profile is NOT updated by this call — it still
        reflects pre-reset state. After calling this, you typically want to
        re-attach (or re-call attach() / calibrate()) to bring the driver back
        in sync with the profile.
        """
        self._require_attached()
        self.raw.restore_defaults()
