"""Profile data model. Pure dataclasses; no I/O, no validation logic.

A `Profile` describes one motor: identity, transport, operating config,
software limits, mechanical info, and characterization results. Loading,
validation, lookup, and saving are added by later v0.1.0 tasks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from mks_servo.constants import WorkMode, Direction


OnViolation = Literal["reject", "clamp", "warn"]


@dataclass
class DriverSection:
    model: str = "servo42d"
    firmware_min: str = "1.0.6"
    slave_addr: int = 1


@dataclass
class TransportSection:
    port: Optional[str] = None
    baud: int = 38400
    timeout_s: float = 3.0


@dataclass
class ConfigSection:
    mode: WorkMode = WorkMode.SR_vFOC
    microsteps: int = 16
    work_current_ma: int = 1500
    hold_current_pct: int = 50
    direction: Direction = Direction.CW


@dataclass
class PositionLimit:
    min_deg: Optional[float] = None
    max_deg: Optional[float] = None
    on_violation: OnViolation = "reject"


@dataclass
class SpeedLimit:
    max_rpm_safe: Optional[int] = None
    on_violation: OnViolation = "clamp"


@dataclass
class CurrentLimit:
    max_ma: int = 3000
    # No on_violation: current always rejects.


@dataclass
class LimitsSection:
    position: PositionLimit = field(default_factory=PositionLimit)
    speed: SpeedLimit = field(default_factory=SpeedLimit)
    current: CurrentLimit = field(default_factory=CurrentLimit)


@dataclass
class OriginSection:
    set_in_firmware: bool = True
    encoder_offset_counts: int = 0


@dataclass
class MechanicalSection:
    motor_model: str = ""
    full_steps_per_rev: int = 200
    gear_ratio: float = 1.0


@dataclass
class PrecisionResults:
    sigma_deg: Optional[float] = None
    peak_deg: Optional[float] = None


@dataclass
class SpeedResults:
    max_measured_rpm: Optional[int] = None
    voltage_v: Optional[float] = None


@dataclass
class CharacterizationSection:
    last_calibrated: Optional[datetime] = None
    precision: PrecisionResults = field(default_factory=PrecisionResults)
    speed: SpeedResults = field(default_factory=SpeedResults)


@dataclass
class Profile:
    id: str
    driver: DriverSection
    schema_version: int = 1
    description: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    transport: TransportSection = field(default_factory=TransportSection)
    config: ConfigSection = field(default_factory=ConfigSection)
    limits: LimitsSection = field(default_factory=LimitsSection)
    origin: OriginSection = field(default_factory=OriginSection)
    mechanical: MechanicalSection = field(default_factory=MechanicalSection)
    characterization: CharacterizationSection = field(default_factory=CharacterizationSection)
    path: Optional[Path] = None
