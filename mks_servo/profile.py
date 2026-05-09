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


# ---------------------------------------------------------------------------
# I/O — Task 5: path-based loading with schema_version check.
# Hierarchical lookup by name is added in Task 7.
# Validation logic belongs to Task 6 and is NOT included here.
# ---------------------------------------------------------------------------

import os  # noqa: E402

from ruamel.yaml import YAML  # noqa: E402  (import after dataclasses section)
from mks_servo.exceptions import ProfileError  # noqa: E402

_yaml = YAML(typ="rt")
_yaml.preserve_quotes = True


def _enum_from_name(enum_cls, name: str, field: str):
    try:
        return enum_cls[name]
    except KeyError as e:
        raise ProfileError(f"unknown {field}: {name!r}") from e


def _to_datetime(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ProfileError(f"invalid datetime: {value!r}")


def _profile_from_dict(d: dict, path: Optional[Path]) -> Profile:
    sv = d.get("schema_version")
    if sv != 1:
        raise ProfileError(f"unknown schema_version: {sv!r} (this build supports 1)")
    if "id" not in d or "driver" not in d:
        raise ProfileError("profile missing required keys: id, driver")

    drv = d["driver"]
    driver = DriverSection(
        model=str(drv.get("model", "servo42d")),
        firmware_min=str(drv.get("firmware_min", "1.0.6")),
        slave_addr=int(drv["slave_addr"]),
    )

    cfg = d.get("config") or {}
    config = ConfigSection(
        mode=_enum_from_name(WorkMode, cfg.get("mode", "SR_vFOC"), "config.mode"),
        microsteps=int(cfg.get("microsteps", 16)),
        work_current_ma=int(cfg.get("work_current_ma", 1500)),
        hold_current_pct=int(cfg.get("hold_current_pct", 50)),
        direction=_enum_from_name(Direction, cfg.get("direction", "CW"), "config.direction"),
    )

    tr = d.get("transport") or {}
    transport = TransportSection(
        port=tr.get("port"),
        baud=int(tr.get("baud", 38400)),
        timeout_s=float(tr.get("timeout_s", 3.0)),
    )

    lim = d.get("limits") or {}
    pos = lim.get("position") or {}
    spd = lim.get("speed") or {}
    cur = lim.get("current") or {}
    limits = LimitsSection(
        position=PositionLimit(
            min_deg=pos.get("min_deg"),
            max_deg=pos.get("max_deg"),
            on_violation=pos.get("on_violation", "reject"),
        ),
        speed=SpeedLimit(
            max_rpm_safe=spd.get("max_rpm_safe"),
            on_violation=spd.get("on_violation", "clamp"),
        ),
        current=CurrentLimit(max_ma=int(cur.get("max_ma", 3000))),
    )

    org = d.get("origin") or {}
    origin = OriginSection(
        set_in_firmware=bool(org.get("set_in_firmware", True)),
        encoder_offset_counts=int(org.get("encoder_offset_counts", 0)),
    )

    mech = d.get("mechanical") or {}
    mechanical = MechanicalSection(
        motor_model=str(mech.get("motor_model", "")),
        full_steps_per_rev=int(mech.get("full_steps_per_rev", 200)),
        gear_ratio=float(mech.get("gear_ratio", 1.0)),
    )

    ch = d.get("characterization") or {}
    pr = ch.get("precision") or {}
    sp = ch.get("speed") or {}
    characterization = CharacterizationSection(
        last_calibrated=_to_datetime(ch.get("last_calibrated")),
        precision=PrecisionResults(sigma_deg=pr.get("sigma_deg"),
                                   peak_deg=pr.get("peak_deg")),
        speed=SpeedResults(max_measured_rpm=sp.get("max_measured_rpm"),
                           voltage_v=sp.get("voltage_v")),
    )

    return Profile(
        id=str(d["id"]),
        driver=driver,
        schema_version=1,
        description=str(d.get("description", "")),
        created_at=_to_datetime(d.get("created_at")),
        updated_at=_to_datetime(d.get("updated_at")),
        transport=transport,
        config=config,
        limits=limits,
        origin=origin,
        mechanical=mechanical,
        characterization=characterization,
        path=path,
    )


def _load_yaml_path(path: Path) -> Profile:
    with path.open("r") as f:
        data = _yaml.load(f)
    if data is None:
        raise ProfileError(f"empty YAML file: {path}")
    return _profile_from_dict(dict(data), path=path)


def _user_profiles_dir() -> Path:
    home = Path(os.environ.get("HOME", str(Path.home())))
    return home / ".config" / "mks-servo" / "profiles"


def _builtin_templates_dir() -> Path:
    return Path(__file__).parent / "profiles" / "_templates"


def _profile_load(cls, name_or_path):
    """Load a profile.

    If `name_or_path` ends with .yaml/.yml AND points to an existing file,
    that file is loaded directly. Otherwise the name is searched in:
      1. ./profiles/<name>.yaml         (project)
      2. ~/.config/mks-servo/profiles/<name>.yaml   (user)
      3. <package>/profiles/_templates/<name>.yaml  (built-in)
    """
    candidate = Path(str(name_or_path))
    if candidate.suffix in (".yaml", ".yml") and candidate.exists():
        return _load_yaml_path(candidate.resolve())

    name = str(name_or_path)
    if not name.endswith((".yaml", ".yml")):
        filename = f"{name}.yaml"
    else:
        filename = name

    search_dirs = [
        Path.cwd() / "profiles",
        _user_profiles_dir(),
        _builtin_templates_dir(),
    ]
    for d in search_dirs:
        p = d / filename
        if p.exists():
            prof = _load_yaml_path(p.resolve())
            # Templates: don't tie save() to the bundled file.
            if d == _builtin_templates_dir():
                prof.path = None
            return prof

    raise ProfileError(
        f"profile not found: {name_or_path!r} "
        f"(searched: {[str(d) for d in search_dirs]})"
    )


Profile.load = classmethod(_profile_load)  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Validation — Task 6: collect ALL violations before raising.
# ---------------------------------------------------------------------------

import re  # noqa: E402

_ID_RE = re.compile(r"^[A-Za-z0-9_\-]+$")
_BAUDS = {9600, 19200, 38400, 57600, 115200}
_KNOWN_MODELS = {"servo42d"}
_VIOLATIONS = ("reject", "clamp", "warn")


def _profile_validate(self) -> None:
    v: list[str] = []

    if not self.id or not _ID_RE.match(self.id):
        v.append(f"id must match {_ID_RE.pattern}, got {self.id!r}")
    if self.schema_version != 1:
        v.append(f"schema_version must be 1, got {self.schema_version}")

    if self.driver.model not in _KNOWN_MODELS:
        v.append(f"driver.model {self.driver.model!r} not in {sorted(_KNOWN_MODELS)}")
    if not (1 <= self.driver.slave_addr <= 247):
        v.append(f"driver.slave_addr must be in 1..247, got {self.driver.slave_addr}")

    if self.transport.baud not in _BAUDS:
        v.append(f"transport.baud must be in {sorted(_BAUDS)}, got {self.transport.baud}")
    if self.transport.timeout_s <= 0:
        v.append(f"transport.timeout_s must be > 0, got {self.transport.timeout_s}")

    c = self.config
    if not (1 <= c.microsteps <= 256):
        v.append(f"config.microsteps must be in 1..256, got {c.microsteps}")
    if not (0 <= c.work_current_ma <= self.limits.current.max_ma):
        v.append(f"config.work_current_ma must be in 0..limits.current.max_ma "
                 f"({self.limits.current.max_ma}), got {c.work_current_ma}")
    if not (10 <= c.hold_current_pct <= 90) or (c.hold_current_pct % 10 != 0):
        v.append(f"config.hold_current_pct must be in 10..90 step 10, got {c.hold_current_pct}")
    if not isinstance(c.mode, WorkMode):
        v.append(f"config.mode must be a WorkMode enum, got {c.mode!r}")
    if not isinstance(c.direction, Direction):
        v.append(f"config.direction must be a Direction enum, got {c.direction!r}")

    pos = self.limits.position
    if (pos.min_deg is None) != (pos.max_deg is None):
        v.append("limits.position.min_deg and max_deg must both be set or both null")
    if pos.min_deg is not None and pos.max_deg is not None and pos.min_deg >= pos.max_deg:
        v.append(f"limits.position min_deg < max_deg required, got {pos.min_deg}/{pos.max_deg}")
    if pos.on_violation not in _VIOLATIONS:
        v.append(f"limits.position.on_violation must be in {_VIOLATIONS}")

    if self.limits.speed.on_violation not in _VIOLATIONS:
        v.append(f"limits.speed.on_violation must be in {_VIOLATIONS}")
    if self.limits.current.max_ma <= 0:
        v.append(f"limits.current.max_ma must be > 0, got {self.limits.current.max_ma}")

    if self.mechanical.gear_ratio <= 0:
        v.append(f"mechanical.gear_ratio must be > 0, got {self.mechanical.gear_ratio}")
    if self.mechanical.full_steps_per_rev <= 0:
        v.append(f"mechanical.full_steps_per_rev must be > 0, got "
                 f"{self.mechanical.full_steps_per_rev}")

    if v:
        raise ProfileError(f"{len(v)} violation(s) in profile {self.id!r}", violations=v)


Profile.validate = _profile_validate  # type: ignore[assignment]
