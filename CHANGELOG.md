# Changelog

All notable changes to mks-servo are documented here.

> Note on ordering: v0.2.1 and v0.3.0/v0.3.1 were developed on parallel
> branches off v0.2.0 and later merged together. They are listed
> newest-version-first below; v0.3.1's tree contains the v0.2.1 multi-motor
> HIL work as well.

## [0.3.1] — 2026-05-11 (Level-2 + CharacterizationSuite HIL-validated)

### Added
- `tests/hil/test_characterize.py` — hardware-in-the-loop coverage of
  `CharacterizationSuite`: P1/P3/P5/S2 sub-tests (run with reduced parameters),
  `update_profile()`, and a full `run_mvp()` end-to-end run.
- `tests/hil/test_namespaces.py` — HIL coverage of `motor.diagnostics`
  (`status_text`, `protection_latched`, `pulses_received`, `release_protection`)
  and the safe part of `motor.advanced` (`set_respond_active`).

### Fixed
- `Motor.attach()` now retries each profile-config write (`set_work_mode`,
  `set_subdivision`, `set_work_current_ma`) once after a 0.3 s settle if it
  hits a `CommTimeout`. The MKS firmware can drop the reply to a command
  issued right after a fresh connection — observed when re-opening the port
  while the motor is still coasting down from a previous session. (HIL.)

### Notes
- `motor.advanced.set_baud()` and `set_slave_addr()` are intentionally not
  HIL-tested: they rewrite driver flash and would break the live connection;
  a failure mid-write could leave the driver on an unknown baud/address. They
  remain covered by the mocked unit tests.
- Known limitation (not changed in this patch release): `run_s2_acceleration`'s
  default sampling window (`samples_per_acc=50 × 0.01 s ≈ 0.5 s`) toward a
  2000 RPM target is too short for this 12 V rig (~1350 RPM ceiling) to reach
  95% of target, so `time_to_target_ms` comes back `[None, …]`. The result is
  still well-formed; `max_observed_rpm` is populated. Revisiting the S2
  defaults is a v0.4 task.

## [0.3.0] — 2026-05-10 (Level-2 namespaces + CharacterizationSuite)

### Added
- `motor.advanced` namespace: `set_baud`, `set_slave_addr`,
  `set_respond_active`, `save_speed_mode_state`. Driver-flash-modifying
  ops grouped here for discoverability.
- `motor.diagnostics` namespace: `protection_latched`, `release_protection`,
  `pulses_received`, `status_text`. Read-only health + protection clears.
- `CharacterizationSuite(motor)` — programmatic empirical tests.
  `run_mvp()` runs P1/P3/P5/S2 and returns a typed `SuiteResult`.
  `update_profile()` writes the precision sigma/peak and the max observed
  RPM into `profile.characterization`.
- CLI `mks-servo characterize <profile> [--suite=mvp|full]
  [--update-profile] [--save] [--port X]`.
- `DRIVER_REGISTRY` + `make_raw_driver(model, **kwargs)` factory in `raw.py`
  — extensibility hook so future SERVO57D support is a registry entry.
- `examples/characterize_motor.py`.
- `docs/characterization.md` — usage reference for the suite.

### Changed
- `Motor.attach()` and `MotorBus.add()`/`scan()` now go through
  `make_raw_driver(model, ...)` instead of constructing `RawDriver`
  directly. Functionally identical for v0.3 users; opens the door to
  per-model raw classes in v0.4+.

### Fixed (backported from v0.1.1, HIL-validated on real SERVO42D hardware)
- `Motor.attach()` opens the serial transport for an internally-owned
  `RawDriver` (it does not auto-open in `__init__`) — the first command after
  attach previously failed with "transport not open".
- `Motor.attach()` energises the motor (Servo-style semantics); `detach()`
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

### Out of scope (deferred)
- `motor.homing.*` and `motor.io.*` namespaces (v0.4).
- Sphinx + readthedocs (v1.0).
- Real SERVO57D driver implementation (registry hook only in v0.3).
- Velocity mode on `Motor` (use `motor.raw.move_speed` for now).

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
