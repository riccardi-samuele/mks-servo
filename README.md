# mks-servo

[![PyPI version](https://img.shields.io/pypi/v/mks-servo.svg)](https://pypi.org/project/mks-servo/)
[![tests](https://github.com/riccardi-samuele/mks-servo/actions/workflows/test.yml/badge.svg)](https://github.com/riccardi-samuele/mks-servo/actions/workflows/test.yml)
[![python](https://img.shields.io/pypi/pyversions/mks-servo.svg)](https://pypi.org/project/mks-servo/)
[![license](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)

Python library for MKS SERVO42D RS485 stepper drivers (NEMA17 / NEMA23 form
factors), with a Servo-style high-level API and per-motor YAML profiles.

```bash
pip install mks-servo
```

## Why

The MKS SERVO42D ships with a 14-bit closed-loop encoder and a rich serial
protocol (~30 opcodes), but no Python library wrapping it at a "set angle,
read angle" level. `mks-servo` does:

- Servo-style API: `motor.write(90)`, `motor.read()`.
- YAML profiles per motor — software limits, mechanical info, calibration
  results travel with the file.
- `mks-servo` CLI for creating, snapshotting, validating, and inspecting
  profiles.

## Install

```bash
pip install mks-servo
```

For development:

```bash
git clone https://github.com/riccardi-samuele/mks-servo.git
cd mks-servo
pip install -e ".[dev,bench]"      # quote the extras; zsh/bash both need it
```

Requires Python 3.10+. The only runtime dependency you'll actually notice
is `pyserial`; everything else is optional or used by the CLI / tests.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup and TDD
workflow.

## Quick start

1. Connect your MKS SERVO42D over RS485 to a USB-RS485 adapter.
2. Snapshot the driver into a profile:

   ```bash
   mks-servo profile from-driver --port /dev/ttyUSB0 --addr 1 --as wrist
   ```

3. Move it from Python:

   ```python
   from mks_servo import Motor

   with Motor.from_profile("wrist") as m:
       m.set_origin()
       m.position_limits = (-90, 90)
       for angle in [0, 45, 90, -45, 0]:
           m.write(angle, rpm=300)
           print(f"target={angle}°  read={m.read():+.2f}°")
   ```

### Multi-motor (v0.2.0+)

Coordinate N motors on the same RS485 bus:

```python
from mks_servo import MotorBus

with MotorBus("/dev/ttyUSB0", baud=38400) as bus:
    wrist = bus.add("./profiles/wrist.yaml")    # slave_addr=1
    elbow = bus.add("./profiles/elbow.yaml")    # slave_addr=2
    wrist.write(45)
    elbow.write(90)
```

Discover what's on the bus and auto-generate profiles for each driver:

```bash
mks-servo bus discover --port /dev/ttyUSB0 --range 1-16 --create-profiles
```

See `examples/dual_motor_bus.py` and `docs/multi-motor.md` for more.

### Characterization (v0.3.0+)

Run empirical tests and persist results into the profile:

```bash
mks-servo characterize wrist --suite=mvp --update-profile --save
```

Or programmatically:

```python
from mks_servo import Motor, CharacterizationSuite

with Motor.from_profile("wrist") as m:
    suite = CharacterizationSuite(m)
    suite.run_mvp()
    suite.update_profile()
    m.profile.save()
```

See `examples/characterize_motor.py` and `docs/characterization.md`.

## API levels

`mks-servo` exposes four progressively richer surfaces. Pick the lowest one
that lets you express what you need:

| Level | Surface | When to use |
|-------|---------|-------------|
| **0** | `Motor.attach/detach/write/read/error/is_moving/emergency_stop` | "Arduino Servo, but more powerful" |
| **1** | `motor.work_current_ma`, `set_origin`, `calibrate`, `move_relative`, properties | Day-to-day robotics code |
| **2** | `motor.advanced.*`, `motor.diagnostics.*` | Flash-rewriting config + health checks |
| **3** | `motor.raw.*` | 1:1 protocol-level control |

`MotorBus` and `CharacterizationSuite` live alongside these on the same
import path.

## Project layout

- `mks_servo/` — library source
  - `motor.py`, `profile.py` — Level 0 + 1 surface and the profile system
  - `bus.py`, `transport.py` — `MotorBus` and the shared, lock-protected RS485 transport
  - `namespaces.py` — Level 2 (`advanced`, `diagnostics`) attached to `Motor`
  - `characterize.py` — `CharacterizationSuite` programmatic P1/P3/P5/S2 tests
  - `raw.py`, `protocol.py`, `constants.py`, `exceptions.py` — Level 3 + framing
  - `cli/` — `mks-servo` command-line tool
- `benchmarks/` — characterization scripts (CSV + PNG output under `results/<timestamp>/`)
- `tests/` — pytest test suite (315 mocked tests + an opt-in HIL suite under `tests/hil/`)
- `docs/` — design docs, specs, characterization reports

## Documentation

- [CHANGELOG](CHANGELOG.md) — release notes for every version
- [CONTRIBUTING](CONTRIBUTING.md) — dev setup, TDD workflow, HIL rig info
- [CODE_OF_CONDUCT](CODE_OF_CONDUCT.md) — Contributor Covenant 2.1
- [Profile schema reference](docs/profiles.md)
- [Multi-motor on one bus](docs/multi-motor.md)
- [Characterization](docs/characterization.md)
- [v0.3.0 design spec](docs/superpowers/specs/2026-05-10-mks-servo-v0.3.0-design.md)
- [v0.2.0 design spec](docs/superpowers/specs/2026-05-10-mks-servo-v0.2.0-design.md)
- [v0.1.0 design spec](docs/superpowers/specs/2026-05-09-mks-servo-v0.1.0-design.md)
- [Long-term vision](docs/superpowers/specs/2026-05-09-mks-servo-vision.md)
- [HIL test report (2026-05-09)](docs/reports/2026-05-09-test-report.md)
- [MKS SERVO42D firmware manual](https://github.com/makerbase-mks/MKS-SERVO42D)

## Status

**1.0.0 — Production/Stable** (released 2026-05-20). HIL-validated on a real
NEMA17 + MKS SERVO42D + 12 V rig: 22 hardware tests + 315 mocked tests +
five-phase soak (1400 moves in 10 min, 0 failures, drift +0.00°).

Level 0/1/3 are fully HIL-validated. Level 2 has three calls
(`AdvancedNamespace.set_baud`/`set_slave_addr`/`save_speed_mode_state`)
marked *experimental* in their docstrings — they rewrite driver flash and
were intentionally kept outside the HIL suite to avoid bricking dev rigs.

## License

Licensed under the [Apache License 2.0](LICENSE). See [NOTICE](NOTICE) for
the attribution notice. The Apache 2.0 patent grant is intentional: this
library is meant to be safe to use in hardware and robotics products.
