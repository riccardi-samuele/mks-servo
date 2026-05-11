# mks-servo

Python library for MKS SERVO42D RS485 stepper drivers (NEMA17 / NEMA23 form
factors), with a Servo-style high-level API and per-motor YAML profiles.

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

This is an early-stage library, not yet on PyPI.

```bash
git clone <this-repo>
cd stepper_motor_test
pip install -e .[dev,bench]
```

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

## Project layout

- `mks_servo/` — library source
  - `motor.py`, `profile.py` — high-level (Level 0+1) and profile system
  - `raw.py`, `transport.py`, `protocol.py` — low-level driver and serial I/O
  - `cli/` — `mks-servo` command-line tool
- `benchmarks/` — characterization scripts (CSV + PNG output under
  `results/<timestamp>/`)
- `tests/` — pytest unit tests
- `docs/` — design docs and characterization reports

## Documentation

- [Profile schema reference](docs/profiles.md)
- [Multi-motor on one bus](docs/multi-motor.md)
- [v0.1.0 design spec](docs/superpowers/specs/2026-05-09-mks-servo-v0.1.0-design.md)
- [v0.2.0 design spec](docs/superpowers/specs/2026-05-10-mks-servo-v0.2.0-design.md)
- [Long-term vision](docs/superpowers/specs/2026-05-09-mks-servo-vision.md)
- [HIL test report (2026-05-09)](docs/reports/2026-05-09-test-report.md)
- [MKS SERVO42D firmware manual](https://github.com/makerbase-mks/MKS-SERVO42D)

## License

Not yet decided. The library is currently a private development; see the
vision document for the planned v1.0.0 open-source release.
