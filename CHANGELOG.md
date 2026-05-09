# Changelog

All notable changes to mks-servo are documented here.

## [0.1.0] — 2026-05-10 (Foundation single-motor)

### Added
- `Motor` class with Level 0 (`attach`/`detach`/`write`/`read`/`error`/
  `is_moving`/`emergency_stop`) and Level 1 (`work_current_ma`,
  `microsteps`, `mode`, `direction`, `hold_current_pct`, `position_limits`,
  `speed_limit_rpm` properties; `set_origin`, `move_relative`,
  `enable`/`disable`, `wait_until_idle`, `calibrate`, `restart`,
  `restore_defaults` methods).
- `Profile` class with YAML schema (`schema_version: 1`),
  `Profile.load`/`save`/`validate`, `from_template`, `from_driver`.
- Bundled template `nema17-bipolar-2A`.
- CLI `mks-servo` with `profile from-driver`/`from-template`/`validate`/`show`.
- New exceptions: `ProfileError`, `LimitExceeded`, `MotorNotAttached`.
- New `RawDriver` opcodes: `set_direction` (cmd 0x85), `set_hold_current_pct` (cmd 0x86).

### Changed
- `MKSServo42D` renamed to `RawDriver`; the alias `MKSServo42D` is kept as
  a deprecated import for v0.1.0 only (will be removed in a follow-up task).
- `transact()` moved from `protocol.py` to a new `transport.py` module.
- `pyproject.toml` package name changed to `mks-servo`; new dependencies:
  `ruamel.yaml`, `click`.

### Internal
- New `tests/conftest.py` with `mock_raw` and `base_profile` fixtures.
- Library refactored in-place from a single-class `MKSServo42D` driver to a
  layered architecture (Motor → Profile → RawDriver → transport).
