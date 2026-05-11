"""HIL: concurrent reads through one SharedTransport must serialise cleanly.
Requires the rig. Two RawDriver handles share the bus's transport and read the
same physical motor from two threads; every reply must be well-formed."""
import threading
import pytest

pytestmark = pytest.mark.hil

_READS_PER_THREAD = 30


def test_concurrent_reads_serialise_on_shared_transport(hil_bus, hil_serial_cfg):
    from mks_servo.raw import RawDriver

    addr = hil_serial_cfg["slave_addr"]
    a = RawDriver(addr=addr, transport=hil_bus._transport)
    b = RawDriver(addr=addr, transport=hil_bus._transport)
    a.open()  # no-op for an externally-owned transport, but mirrors real usage
    b.open()

    errors: list[tuple[str, str]] = []
    counts = {"a": 0, "b": 0}
    barrier = threading.Barrier(2)

    def worker(drv, key):
        try:
            barrier.wait()  # maximise the chance of true interleaving
            for _ in range(_READS_PER_THREAD):
                v = drv.read_encoder_addition()
                assert isinstance(v, int)
                counts[key] += 1
        except Exception as exc:  # noqa: BLE001 - we want to see *anything*
            errors.append((key, repr(exc)))

    ta = threading.Thread(target=worker, args=(a, "a"), name="hil-reader-a")
    tb = threading.Thread(target=worker, args=(b, "b"), name="hil-reader-b")
    ta.start(); tb.start()
    ta.join(timeout=30); tb.join(timeout=30)

    assert not ta.is_alive() and not tb.is_alive(), "a reader thread hung (deadlock?)"
    assert not errors, f"concurrent reads produced errors: {errors}"
    assert counts == {"a": _READS_PER_THREAD, "b": _READS_PER_THREAD}


def test_concurrent_mixed_reads_no_cross_talk(hil_bus, hil_serial_cfg):
    """Two threads issuing *different* read opcodes concurrently. Each reply is
    decoded by the same RawDriver that sent the request; if the lock leaked, a
    thread would parse the other's reply and the typed accessor would blow up
    (wrong length / bad checksum / nonsense enum value)."""
    from mks_servo.raw import RawDriver

    addr = hil_serial_cfg["slave_addr"]
    a = RawDriver(addr=addr, transport=hil_bus._transport)
    b = RawDriver(addr=addr, transport=hil_bus._transport)
    a.open(); b.open()

    errors: list[tuple[str, str]] = []
    barrier = threading.Barrier(2)

    def read_encoder():
        try:
            barrier.wait()
            for _ in range(_READS_PER_THREAD):
                assert isinstance(a.read_encoder_addition(), int)
        except Exception as exc:  # noqa: BLE001
            errors.append(("encoder", repr(exc)))

    def read_status_and_speed():
        from mks_servo.raw import MotorStatus
        try:
            barrier.wait()
            for _ in range(_READS_PER_THREAD):
                st = b.read_motor_status()
                assert isinstance(st, MotorStatus)
                assert isinstance(b.read_speed_rpm(), int)
        except Exception as exc:  # noqa: BLE001
            errors.append(("status", repr(exc)))

    t1 = threading.Thread(target=read_encoder, name="hil-encoder")
    t2 = threading.Thread(target=read_status_and_speed, name="hil-status")
    t1.start(); t2.start()
    t1.join(timeout=30); t2.join(timeout=30)

    assert not t1.is_alive() and not t2.is_alive(), "a reader thread hung (deadlock?)"
    assert not errors, f"concurrent mixed reads produced errors: {errors}"
