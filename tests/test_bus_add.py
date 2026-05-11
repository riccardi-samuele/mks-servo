from unittest.mock import patch
from mks_servo.bus import MotorBus
from mks_servo.profile import Profile, DriverSection


def _make_profile(addr=1, mid="t"):
    return Profile(id=mid, driver=DriverSection(model="servo42d", slave_addr=addr))


def test_add_returns_attached_motor():
    with patch("mks_servo.transport.serial.Serial"):
        with MotorBus("/dev/foo") as bus:
            with patch.object(bus._transport, "transact",
                              return_value=(1, 0x82, b"\x01")):
                m = bus.add(_make_profile())
                assert m.profile.id == "t"
                assert m._attached
                assert len(bus) == 1
                assert m in bus


def test_add_multiple_motors_share_transport():
    with patch("mks_servo.transport.serial.Serial"):
        with MotorBus("/dev/foo") as bus:
            with patch.object(bus._transport, "transact",
                              return_value=(1, 0x82, b"\x01")):
                m1 = bus.add(_make_profile(addr=1, mid="a"))
                m2 = bus.add(_make_profile(addr=2, mid="b"))
                assert m1.raw._transport is bus._transport
                assert m2.raw._transport is bus._transport
                assert len(bus) == 2


def test_remove_detaches_motor():
    with patch("mks_servo.transport.serial.Serial"):
        with MotorBus("/dev/foo") as bus:
            with patch.object(bus._transport, "transact",
                              return_value=(1, 0x82, b"\x01")):
                m = bus.add(_make_profile())
                bus.remove(m)
                assert len(bus) == 0
                assert not m._attached


def test_remove_unknown_motor_is_noop():
    """Removing a motor that was never added should not raise."""
    from mks_servo.motor import Motor
    from mks_servo.raw import RawDriver
    fake_transport = None
    with patch("mks_servo.transport.serial.Serial"):
        with MotorBus("/dev/foo") as bus:
            # Build a Motor that's NOT in bus._motors:
            other = Motor(_make_profile(),
                          raw=RawDriver(addr=1, transport=bus._transport))
            bus.remove(other)  # should silently do nothing
            assert len(bus) == 0


def test_iterate_motors():
    with patch("mks_servo.transport.serial.Serial"):
        with MotorBus("/dev/foo") as bus:
            with patch.object(bus._transport, "transact",
                              return_value=(1, 0x82, b"\x01")):
                m1 = bus.add(_make_profile(addr=1, mid="a"))
                m2 = bus.add(_make_profile(addr=2, mid="b"))
                ids = [m.profile.id for m in bus]
                assert ids == ["a", "b"]


def test_close_detaches_all_motors():
    with patch("mks_servo.transport.serial.Serial"):
        bus = MotorBus("/dev/foo")
        bus.open()
        with patch.object(bus._transport, "transact",
                          return_value=(1, 0x82, b"\x01")):
            m1 = bus.add(_make_profile(addr=1, mid="a"))
            m2 = bus.add(_make_profile(addr=2, mid="b"))
        bus.close()
        assert not m1._attached
        assert not m2._attached
        assert len(bus) == 0
