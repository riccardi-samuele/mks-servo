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

from pathlib import Path
from typing import Optional, Union

from mks_servo.exceptions import MotorNotAttached
from mks_servo.profile import Profile
from mks_servo.raw import RawDriver


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

    # ─── Read-only convenience ─────────────────────────────────────────
    @property
    def model(self) -> str:
        return self.profile.driver.model
