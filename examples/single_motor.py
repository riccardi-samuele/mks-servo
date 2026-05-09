"""Single motor example.

Usage:
    python examples/single_motor.py

Requires a profile at ./profiles/wrist.yaml. Create one with:
    mks-servo profile from-template nema17-bipolar-2A --as wrist
or:
    mks-servo profile from-driver --port /dev/ttyUSB0 --addr 1 --as wrist
"""
from mks_servo import Motor


def main() -> None:
    with Motor.from_profile("wrist") as m:
        m.set_origin()
        m.position_limits = (-90, 90)
        for angle in [0, 45, 90, -45, 0]:
            m.write(angle, rpm=300)
            print(f"target={angle:+3d}°  read={m.read():+.2f}°  "
                  f"err={m.error():+.3f}°")


if __name__ == "__main__":
    main()
