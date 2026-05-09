"""Two-motor coordination on a single RS485 bus.

Usage:
    python examples/dual_motor_bus.py

Requires two profiles:
  ./profiles/wrist.yaml (slave_addr=1)
  ./profiles/elbow.yaml (slave_addr=2)

Create them with:
    mks-servo bus discover --port /dev/ttyUSB0 --range 1-16 --create-profiles
which auto-generates motor_<addr>.yaml for every responsive driver. Then
rename to wrist.yaml / elbow.yaml as needed.
"""
from mks_servo import MotorBus


def main() -> None:
    with MotorBus("/dev/ttyUSB0", baud=38400) as bus:
        wrist = bus.add("./profiles/wrist.yaml")
        elbow = bus.add("./profiles/elbow.yaml")
        for w_target, e_target in [(0, 0), (45, -45), (90, -90), (0, 0)]:
            wrist.write(w_target, blocking=False)
            elbow.write(e_target, blocking=True)   # block on the slowest
            wrist.wait_until_idle()
            print(f"wrist={wrist.read():+.2f}°  elbow={elbow.read():+.2f}°")


if __name__ == "__main__":
    main()
