# Changelog

All notable changes to mks-servo are documented here.

## [0.2.1] — 2026-05-11 (Multi-motor layer HIL-validated)

### Added
- `tests/hil/test_bus_smoke.py`, `test_bus_lifecycle.py`, `test_bus_scan.py`,
  `test_bus_concurrent.py` — hardware-in-the-loop coverage of `MotorBus` /
  `SharedTransport` / externally-owned `RawDriver` on a real NEMA17 + SERVO42D
  + 12V rig. `test_bus_two_motors.py` (gated on `$MKS_HIL_SECOND_ADDR`) adds a
  two-motors-on-one-bus concurrency test.
- `tests/hil/conftest.py`: `hil_serial_cfg` and `hil_bus` fixtures.

### Notes
- The v0.2.0 multi-motor layer passed the new HIL suite on the first run with
  **no production code changes** — the `threading.Lock` in `SharedTransport`
  serialises concurrent bus traffic correctly on real hardware (concurrent
  reads from two `RawDriver` handles on one transport produced no corrupt
  frames). `MotorBus.add()`/`remove()`/`scan()`/context-manager teardown all
  behave on hardware.

### Fixed (backported from v0.1.1, HIL-validated on real SERVO42D hardware)
- `Motor.attach()` now opens the serial transport for an internally-owned
  `RawDriver` (it does not auto-open in `__init__`) — the first command after
  attach previously failed with "transport not open".
- `Motor.attach()` now energises the motor (Servo-style semantics); `detach()`
  still disables it. Without this, `motor.write()` commands were accepted by
  the driver but the motor stayed physically inert.
- `Motor.write(timeout=None)` / `Motor.wait_until_idle()` no longer forward
  `timeout=None` into `RawDriver.wait_until_idle`, which crashed its deadline
  arithmetic.
- `RawDriver.wait_until_idle` tolerates the SERVO42D firmware V1.0.6 quirk
  where status (cmd 0xF1) latches in `SPEED_DOWN` indefinitely after a
  closed-loop move: it now also accepts `speed_rpm == 0` for N consecutive
  reads as the idle signal, requires observed motion or `min_warmup_s` before
  counting zero-streaks (so a no-op move doesn't return prematurely), defaults
  to a 0.2s poll interval, and tolerates one `CommTimeout` per iteration
  (truncated frames during motion).
- `Motor.set_origin(soft=False)` adds a 0.2s settle pause + one retry on
  `CommTimeout` (cmd 0x92 occasionally times out right after a motion).

## [0.2.0] — 2026-05-10 (Multi-motor + raw promoted)

### Added
- `MotorBus(port, baud)` — multi-motor coordinator on a shared RS485 bus.
  `bus.add(profile)` constructs a `Motor` sharing the bus's transport and
  attaches it automatically. `bus.remove(motor)` detaches.
- `MotorBus.scan(addr_range)` — probe a range of slave addresses and return
  a list of `BusEntry` for responsive drivers. Optional `create_profiles=True`
  generates `motor_<addr>.yaml` files.
- `SharedTransport` — wraps `serial.Serial` + `threading.Lock`, enabling
  multiple `RawDriver` instances on one physical bus with serialised I/O.
- CLI `mks-servo bus discover --port X` (with `--range`, `--baud`, `--timeout`,
  `--create-profiles`, `--out`, `--force`).
- `Profile.snapshot_from(motor)` — refreshes the `config:` section from the
  driver's current state; does not save (caller invokes `save()`).
- `Motor(profile, auto_save=True)` — opt-in profile write-through. After
  every Level-1 mutating operation (setters, `set_origin`, `calibrate`,
  `restart`), the profile is persisted to YAML. Default `auto_save=False`
  preserves v0.1.0 behaviour.
- `examples/single_motor.py`, `examples/dual_motor_bus.py`.
- `docs/multi-motor.md` — addressing, discovery, locking notes.
- Public `motor.raw` (Level 3 official API).

### Changed (BREAKING)
- `motor._raw` removed; use `motor.raw` instead. Pre-v1.0 break per the
  decisions log in the vision document.
- `RawDriver.__init__(transport=...)` accepts an external `SharedTransport`;
  when provided, `port` is optional and `open()`/`close()` become no-ops
  (the bus owns lifecycle). Backwards compatible: `RawDriver(port="/dev/...")`
  still works as before.

### Internal
- `RawDriver._txn()` now routes exclusively through `SharedTransport.transact()`;
  the module-level `transact()` function is kept for direct use but not
  called by `RawDriver` anymore.

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
