# mks-servo — Vision Document

**Status:** Vision (non-implementation). Principles and phased roadmap.
**Date:** 2026-05-09
**Owner:** Samuele
**Scope:** Long-term direction of the `mks-servo` Python library.

---

## 1. Why this library exists

The MKS SERVO42D / SERVO57D drivers are inexpensive closed-loop stepper drivers
(NEMA17 / NEMA23 form factor) with an integrated 14-bit encoder. They expose a
serial protocol (RS485 native + Modbus-RTU) with ~30 opcodes covering motion,
configuration, calibration, persistence, and diagnostics.

There is no Python library that:
1. Wraps the protocol with a *Servo-like* high-level API ("set angle, read angle"),
   accessible to users who don't want to know about opcodes;
2. Lets advanced users reach every parameter the firmware exposes, without
   forcing them down to raw frame I/O;
3. Captures motor identity, limits, calibration, and characterization in
   **portable profile files** that can be shared between projects and
   versioned in git;
4. Supports N heterogeneous motors on the same RS485 bus with mixed models
   and mixed configurations, each governed by its own profile;
5. Enables empirical characterization of a motor (precision, max RPM, stall
   threshold, persistence) and writes the results back into the profile.

This library fills that gap.

## 2. Audience

- **Primary**: makers and roboticists building projects with a small number
  (1–10) of MKS SERVO motors and standard NEMA17/23 motors. They want a
  library that "just works" out of the box, with a learning curve close to
  Arduino's `Servo`.
- **Secondary**: researchers and engineers who need fine-grained control over
  every firmware parameter, without giving up the convenience of high-level
  motion calls.
- **Tertiary**: contributors who want to extend the library to other MKS
  drivers (SERVO57D) or to add features (homing routines, characterization
  suites). The architecture must make this easy.

## 3. Architectural principles

### 3.1 Progressive disclosure (4 levels)

The API is layered. Each level is opt-in: users start at Level 0, descend
only when they need to.

| Level | Surface | Intended use |
|---|---|---|
| **0** | 7 base methods on `Motor`: `attach/detach/write/read/error/is_moving/emergency_stop` | Quick start, scripting, "Servo-style" |
| **1** | Properties: `work_current_ma`, `microsteps`, `mode`, `direction`, `position_limits`, `speed_limit_rpm`, ... | Tuning, configuration |
| **2** | Namespaced advanced features: `motor.advanced.*`, `motor.homing.*`, `motor.io.*`, `motor.diagnostics.*` | Power users, integrators |
| **3** | Raw protocol access: `motor.raw.*` (every opcode 1:1 with the manual) | Protocol research, edge cases |

A user who never opens the Level 2/3 namespaces should never be confused by
their existence. A user who needs Level 3 should not have to monkey-patch.

### 3.2 Profile-driven configuration

A **profile** is a YAML file describing one motor: model, transport, operating
config, software limits, mechanical info, characterization results. The
profile is the single source of truth for that motor. Profiles are:

- **Portable** — a YAML file you can copy between projects, version in git,
  share with collaborators.
- **Validated** — a strict schema (versioned: `schema_version: 1`). Schema
  upgrades migrate automatically.
- **Composable** — one profile per motor; multiple profiles attach to a single
  bus.
- **Round-trippable** — comments survive save/load (parser: `ruamel.yaml`).
- **Auto-creatable** — five graduated modes for v0.x, from "fill in a template"
  to "scan the bus, introspect every driver, run the characterization suite,
  write the YAMLs." Not all are in v0.1.0; see roadmap.

### 3.3 Limits live in the profile, not in code

The firmware exposes some hardware-level safety (current cap, mode-dependent
RPM cap), but does not enforce arbitrary user-defined limits like "this joint
must stay between -90° and +90°." Such limits belong to the *profile*, are
applied by the high-level `Motor` class before any raw call, and have a
configurable violation policy (`reject` / `clamp` / `warn`).

This is the single feature that justifies the existence of `Motor` over
`RawDriver`. A user who calls `motor.write(200)` on a profile with
`max_deg: 180` should never reach the wire.

### 3.4 Heterogeneous bus support

The library is designed from day one to support N different motors on the
same bus. v0.1.0 ships single-motor only (YAGNI for the first release), but
nothing in the architecture forecloses multi-motor — `Motor` does not own the
serial transport, `MotorBus` does (introduced in v0.2.0).

### 3.5 Family-friendly defaults

The library's defaults must be safe for an unsupervised motor on a bench:
limits enabled, current capped at the profile value, position rejection on by
default for software limits. Surprising the user with a fast spinning motor
or a burned coil is unacceptable.

## 4. Profile schema (overview)

A profile file contains seven top-level sections:

- `driver` — model, slave address, firmware version
- `transport` — serial port, baud, timeout (optional, can be passed at runtime)
- `config` — operating parameters written to the driver (mode, current,
  microsteps, direction, hold current)
- `limits` — software-enforced position/speed/current limits with violation
  policies
- `origin` — zero policy (firmware vs software offset)
- `mechanical` — descriptive info (motor model, gear ratio, full steps/rev)
- `characterization` — empirical results from the test suite (optional)

Every field has a default. The minimum viable profile is just `id`,
`schema_version`, `driver.model`, and `driver.slave_addr`.

The full schema for `schema_version: 1` lives in the v0.1.0 design doc.

## 5. Roadmap (versioned phases)

### v0.1.0 — Foundation single-motor (~2–3 weeks)

- `Motor` class: Level 0 (7 methods) + Level 1 (properties + extra methods)
- `Profile` class: schema v1 + validation + `from_template` + `from_driver`
- CLI: `from-driver`, `from-template`, `validate`, `show`
- Refactor: `MKSServo42D` → `RawDriver` (private, behind `motor._raw`)
- Existing benchmarks migrated to use `Motor`
- Unit tests + 3 HIL smoke tests

**Not yet**: multi-motor, auto-discover, characterize, public `motor.raw`,
async, advanced/homing/io/diagnostics namespaces, Sphinx docs, PyPI release.

### v0.2.0 — Multi-motor + raw promoted (~3–4 weeks after v0.1.0)

- `MotorBus` for N heterogeneous motors on one transport
- `motor.raw.*` promoted to public API (Level 3 official)
- `auto-discover` CLI command
- Profile auto-update / write-through (opt-in)
- Multi-motor examples

### v0.3.0 — Testing framework + characterize (~4–6 weeks after v0.2.0)

- `motor.advanced.*`, `motor.homing.*`, `motor.io.*`, `motor.diagnostics.*`
  namespaces (Level 2)
- `CharacterizationSuite` — P1/P3/P5/V1/S1/S2/S3/C1/C2/C3 ported from
  `benchmarks/` with profile auto-update
- CLI: `characterize <profile> --suite=mvp|full`
- Sphinx + readthedocs
- Tentative SERVO57D support

### v1.0.0 — Stable, open source (~2–3 months tail)

- API freeze; semver guarantees from here on
- License chosen (candidates: Apache-2.0 or MIT)
- PyPI publish + GitHub public release
- Community standards (CONTRIBUTING.md, CODE_OF_CONDUCT.md, issue templates)

## 6. Out of scope (explicit non-goals)

- **Async API**: synchronous is fine for scripting and HIL use cases. Adding
  async would double the maintenance surface for marginal benefit.
- **Other vendors**: this library is MKS-specific. A user who wants
  smoothieboard or FYSETC support should use a different library or extend
  this one in a fork.
- **ROS 2 nodes**: a separate repo can wrap this library as a ROS 2 node.
  Not part of `mks-servo` core.
- **Web dashboard / GUI**: out of scope. CLI + Python API only.
- **Simulator / digital twin**: out of scope.
- **Move profiles beyond trapezoidal**: the firmware's trapezoidal
  acceleration is enough. S-curve / jerk-limited profiles are not planned.

## 7. Decisions log

Major decisions made during brainstorming, recorded here for posterity:

| Decision | Rationale |
|---|---|
| YAML for profiles (not TOML/JSON) | Comments preserved, expressive nesting, robotics standard |
| `ruamel.yaml` parser | Round-trip preservation of comments |
| `Motor` does not call opcodes directly | Single point for limits/units; `RawDriver` reusable for Level 3 |
| Limits in profile, not code | Per-motor configurability; portable across projects |
| Single-motor v0.1.0 (vs full multi-motor) | Risk reduction; nothing forecloses v0.2.0 |
| Open source publish at v1.0.0 (not earlier) | API maturity before community contact |
| Synchronous-only API | Async would double maintenance surface |
| `mode` setter does silent `restart()` | Matches HIL finding (cap RPM doesn't apply otherwise) |
| Driver-level zero (cmd 0x92) is default `set_origin()` | Persistence across power-cycle is robotics-critical |

---

End of vision.
