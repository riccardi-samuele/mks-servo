"""Profile data model. Pure dataclasses; no I/O, no validation logic.

A `Profile` describes one motor: identity, transport, operating config,
software limits, mechanical info, and characterization results. Loading,
validation, lookup, and saving are added by later v0.1.0 tasks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
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


def _profile_from_template(cls, template_name: str, *, id: str) -> "Profile":
    """Construct a Profile from a built-in template.

    The returned profile has `path=None` (no auto-save target). The `id` and
    `created_at` are overridden; everything else is copied from the template.
    """
    template_path = _builtin_templates_dir() / f"{template_name}.yaml"
    if not template_path.exists():
        raise ProfileError(
            f"template not found: {template_name!r} "
            f"(available in {_builtin_templates_dir()})"
        )
    prof = _load_yaml_path(template_path)
    prof.id = id
    prof.path = None
    prof.created_at = datetime.now(timezone.utc)
    prof.updated_at = prof.created_at
    return prof


Profile.from_template = classmethod(_profile_from_template)  # type: ignore[assignment]


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


# ---------------------------------------------------------------------------
# Profile.from_driver — Task 9: introspection via cmd 0x47 (read_all_config).
# ---------------------------------------------------------------------------

from mks_servo.constants import BaudRate  # noqa: E402


# BaudRate code → bps lookup built from the BaudRate enum.
# Example: code 4 → 38400, code 6 → 115200.
_BAUD_CODE_TO_BPS: dict[int, int] = {br.code: br.bps for br in BaudRate}

# hold_current_pct_idx → percentage.
# The firmware encodes hold current as an index 0-8, where each step is 10%.
# Index 0 → 10%, index 1 → 20%, …, index 8 → 90%.
_HOLD_IDX_TO_PCT: dict[int, int] = {i: (i + 1) * 10 for i in range(9)}


def _profile_from_driver(cls, raw, *, id: str) -> "Profile":
    """Snapshot a connected RawDriver into a fresh Profile.

    Reads ``read_all_config()`` (cmd 0x47) from the driver and populates the
    ``driver``, ``transport.baud``, and ``config`` sections.  ``limits``,
    ``mechanical``, and ``characterization`` get default values — they are not
    knowable from the driver alone.

    Translation from raw read_all_config() dict to Profile fields:
      - info["mode"]               raw int → WorkMode(int)
      - info["current_ma"]         milliamps → config.work_current_ma
      - info["hold_current_pct_idx"] index 0-8 → percentage (idx+1)*10
      - info["subdivision"]        microsteps int → config.microsteps
      - info["dir_cw"]             bool True→CW / False→CCW → Direction enum
      - info["slave_addr"]         raw int → driver.slave_addr
      - info["baud_code"]          BaudRate.code → bps via _BAUD_CODE_TO_BPS

    Returns a Profile with ``path=None``. Caller is responsible for ``save()``.
    """
    info = raw.read_all_config()

    # Translate baud_code (e.g. 4) → bps (e.g. 38400).
    baud_code = int(info["baud_code"])
    baud_bps = _BAUD_CODE_TO_BPS.get(baud_code, 38400)

    # Translate hold_current_pct_idx (0-8) → percentage (10-90 step 10).
    hold_idx = int(info["hold_current_pct_idx"])
    hold_pct = _HOLD_IDX_TO_PCT.get(hold_idx, 50)  # default 50% on unknown index

    # Translate dir_cw bool → Direction enum (True=CW, False=CCW).
    direction = Direction.CW if info["dir_cw"] else Direction.CCW

    prof = Profile(
        id=id,
        driver=DriverSection(model="servo42d", slave_addr=int(info["slave_addr"])),
        config=ConfigSection(
            mode=WorkMode(int(info["mode"])),
            microsteps=int(info["subdivision"]),
            work_current_ma=int(info["current_ma"]),
            hold_current_pct=hold_pct,
            direction=direction,
        ),
        transport=TransportSection(baud=baud_bps),
    )
    prof.created_at = datetime.now(timezone.utc)
    prof.updated_at = prof.created_at
    return prof


Profile.from_driver = classmethod(_profile_from_driver)  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Profile.snapshot_from(motor) — Task 10: refresh config from connected driver.
# ---------------------------------------------------------------------------

def _profile_snapshot_from(self, motor) -> None:
    """Read motor.raw.read_all_config() and overwrite this profile's `config:`
    section. The driver's `slave_addr` is also refreshed. Other sections
    (limits, mechanical, characterization) are NOT touched. Caller invokes
    save() to persist."""
    info = motor.raw.read_all_config()
    self.config.mode = info["mode"]
    self.config.work_current_ma = int(info["current_ma"])
    self.config.microsteps = int(info["subdivision"])
    self.config.hold_current_pct = (int(info["hold_current_pct_idx"]) + 1) * 10
    self.config.direction = Direction.CW if info["dir_cw"] else Direction.CCW
    self.driver.slave_addr = int(info["slave_addr"])


Profile.snapshot_from = _profile_snapshot_from  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Profile.save() — Task 10: write profile back to YAML preserving comments.
# ---------------------------------------------------------------------------

def _profile_to_dict(prof: "Profile") -> dict:
    """Convert a Profile to a plain dict ordered for human readability."""
    def _dt(d):
        return d.isoformat() if d is not None else None
    return {
        "schema_version": prof.schema_version,
        "id": prof.id,
        "description": prof.description,
        "created_at": _dt(prof.created_at),
        "updated_at": _dt(prof.updated_at),
        "driver": {
            "model": prof.driver.model,
            "firmware_min": prof.driver.firmware_min,
            "slave_addr": prof.driver.slave_addr,
        },
        "transport": {
            "port": prof.transport.port,
            "baud": prof.transport.baud,
            "timeout_s": prof.transport.timeout_s,
        },
        "config": {
            "mode": prof.config.mode.name,
            "microsteps": prof.config.microsteps,
            "work_current_ma": prof.config.work_current_ma,
            "hold_current_pct": prof.config.hold_current_pct,
            "direction": prof.config.direction.name,
        },
        "limits": {
            "position": {
                "min_deg": prof.limits.position.min_deg,
                "max_deg": prof.limits.position.max_deg,
                "on_violation": prof.limits.position.on_violation,
            },
            "speed": {
                "max_rpm_safe": prof.limits.speed.max_rpm_safe,
                "on_violation": prof.limits.speed.on_violation,
            },
            "current": {"max_ma": prof.limits.current.max_ma},
        },
        "origin": {
            "set_in_firmware": prof.origin.set_in_firmware,
            "encoder_offset_counts": prof.origin.encoder_offset_counts,
        },
        "mechanical": {
            "motor_model": prof.mechanical.motor_model,
            "full_steps_per_rev": prof.mechanical.full_steps_per_rev,
            "gear_ratio": prof.mechanical.gear_ratio,
        },
        "characterization": {
            "last_calibrated": _dt(prof.characterization.last_calibrated),
            "precision": {
                "sigma_deg": prof.characterization.precision.sigma_deg,
                "peak_deg": prof.characterization.precision.peak_deg,
            },
            "speed": {
                "max_measured_rpm": prof.characterization.speed.max_measured_rpm,
                "voltage_v": prof.characterization.speed.voltage_v,
            },
        },
    }


def _deep_update(dst, src):
    """In-place merge of src into dst preserving dst's structure (for ruamel)."""
    for k, v in src.items():
        if isinstance(v, dict) and k in dst and isinstance(dst[k], dict):
            _deep_update(dst[k], v)
        else:
            dst[k] = v


def _profile_save(self, path: Optional[Path] = None) -> None:
    """Save the profile to YAML.

    If `path` is None, writes back to `self.path`. If both are None
    (template-loaded profile), raises ProfileError.

    Round-trip note: if the profile was loaded from a YAML file, comments and
    field ordering are preserved. If it was constructed in memory, the output
    follows a canonical order.
    """
    target = Path(path) if path is not None else self.path
    if target is None:
        raise ProfileError(
            "no path: profile was loaded from a template or constructed in memory; "
            "pass an explicit path to save()"
        )

    self.updated_at = datetime.now(timezone.utc)

    # Round-trip path: re-read original file (if any) so ruamel preserves comments.
    if self.path is not None and self.path.exists():
        with self.path.open("r") as f:
            data = _yaml.load(f) or {}
        new = _profile_to_dict(self)
        _deep_update(data, new)
    else:
        data = _profile_to_dict(self)

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w") as f:
        _yaml.dump(data, f)
    self.path = target.resolve()


Profile.save = _profile_save  # type: ignore[assignment]
