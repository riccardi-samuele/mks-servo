# Quickstart

Drive a single MKS SERVO42D closed-loop stepper over RS485 in ~10 lines of
Python.

## Hardware checklist

- MKS SERVO42D driver on the bus, slave address known (factory default `1`).
- USB-to-RS485 adapter (FT232 / CH340 recommended). Direct USB port, not a
  hub — the soak run that motivated v1.0 caught a flaky hub adapter.
- 12–24&nbsp;V driver supply, NEMA17 motor wired A1/A2/B1/B2.
- `/dev/ttyUSB0` (Linux) or equivalent COM port.

## Wire a profile

A profile is a YAML file that describes one motor. Generate one from a
bundled template, or scan a live bus.

```bash
mks-servo profile from-template nema17-bipolar-2A --slave-addr 1 \
    --port /dev/ttyUSB0 --baud 38400 > my_motor.yaml
```

For a multi-motor bus, the scanner emits one profile per responding driver:

```bash
mks-servo bus discover --port /dev/ttyUSB0 --range 1-10 --create-profiles
```

## Move a motor

```python
from mks_servo import Motor, Profile

profile = Profile.load("my_motor.yaml")

with Motor(profile) as m:
    m.set_origin()
    m.move_relative(degrees=90, rpm=120)
    m.wait_until_idle()
    print("angle:", m.angle_degrees, "deg")
```

`Motor` opens the serial transport in `attach()`, energises the motor with
Servo-style semantics, then `detach()` (driven by the context manager)
disables it cleanly.

## Add a second motor on the same bus

```python
from mks_servo import MotorBus, Profile

with MotorBus(port="/dev/ttyUSB0", baud=38400) as bus:
    a = bus.add(Profile.load("base.yaml"))      # addr 1
    b = bus.add(Profile.load("wrist.yaml"))     # addr 2
    a.move_relative(degrees=30, rpm=60)
    b.move_relative(degrees=-45, rpm=90)
    a.wait_until_idle()
    b.wait_until_idle()
```

`MotorBus` shares a single `SharedTransport` across motors and serialises
RS485 traffic with an internal lock.

## Next steps

- See [Profiles](profiles.md) for the YAML schema.
- See [Multi-motor](multi-motor.md) for addressing and discovery.
- See [Characterization](characterization.md) to record empirical precision
  and speed envelopes into a profile.
- See [FAQ](faq.md) for firmware quirks that bit us during HIL bring-up.
