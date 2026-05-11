"""HIL: two motors on one RS485 bus moving simultaneously. Requires a second
SERVO42D at the address given in $MKS_HIL_SECOND_ADDR; self-skips otherwise."""
import copy
import os
import threading
import pytest

pytestmark = pytest.mark.hil

_SECOND_ADDR_ENV = "MKS_HIL_SECOND_ADDR"


@pytest.fixture
def second_addr():
    val = os.environ.get(_SECOND_ADDR_ENV)
    if not val:
        pytest.skip(f"set {_SECOND_ADDR_ENV}=<addr> to run the two-motor HIL test")
    return int(val)


def test_two_motors_move_concurrently(second_addr, hil_bus, hil_profile):
    # `second_addr` is listed first so the skip (when the env var is unset)
    # fires before `hil_bus` tries to open the serial port.
    p1 = hil_profile
    p2 = copy.deepcopy(hil_profile)
    p2.id = "hil_test_2"
    p2.driver.slave_addr = second_addr

    m1 = hil_bus.add(p1)
    m2 = hil_bus.add(p2)
    assert len(hil_bus) == 2

    m1.set_origin(); m2.set_origin()

    barrier = threading.Barrier(2)
    errors: list[str] = []

    def move(motor, target):
        try:
            barrier.wait()
            motor.write(target, rpm=300)  # blocking: returns when idle
        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc))

    t1 = threading.Thread(target=move, args=(m1, 40.0), name="hil-m1")
    t2 = threading.Thread(target=move, args=(m2, 70.0), name="hil-m2")
    t1.start(); t2.start()
    t1.join(timeout=30); t2.join(timeout=30)

    assert not t1.is_alive() and not t2.is_alive(), "a motor thread hung"
    assert not errors, f"concurrent moves errored: {errors}"
    assert abs(m1.read() - 40.0) < 1.5
    assert abs(m2.read() - 70.0) < 1.5

    m1.write(0); m2.write(0)
