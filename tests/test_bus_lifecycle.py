from unittest.mock import MagicMock, patch
from mks_servo.bus import MotorBus, BusEntry


def test_bus_construction_does_not_open_transport():
    bus = MotorBus("/dev/foo", baud=38400)
    assert bus._transport is not None
    assert bus._transport._ser is None  # not yet open


def test_bus_open_close():
    with patch("mks_servo.transport.serial.Serial") as fake_serial_cls:
        bus = MotorBus("/dev/foo")
        bus.open()
        fake_serial_cls.assert_called_once()
        bus.close()


def test_bus_context_manager():
    with patch("mks_servo.transport.serial.Serial") as fake_serial_cls:
        with MotorBus("/dev/foo") as bus:
            assert bus._transport._ser is not None
        # On exit, close was called
        assert bus._transport._ser is None


def test_bus_initially_empty():
    bus = MotorBus("/dev/foo")
    assert len(bus) == 0
    assert list(bus) == []


def test_bus_passes_baud_and_timeout_to_transport():
    bus = MotorBus("/dev/foo", baud=115200, timeout=5.0)
    assert bus._transport.baud == 115200
    assert bus._transport.timeout == 5.0


def test_bus_entry_is_a_dataclass():
    e = BusEntry(addr=1, model="servo42d", config={"x": 1})
    assert e.addr == 1
    assert e.model == "servo42d"
    assert e.config == {"x": 1}
    assert e.profile is None
