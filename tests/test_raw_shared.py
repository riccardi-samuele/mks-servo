from unittest.mock import MagicMock
from mks_servo.raw import RawDriver
from mks_servo.transport import SharedTransport


def test_raw_driver_accepts_external_transport():
    fake_t = MagicMock(spec=SharedTransport)
    raw = RawDriver(addr=1, transport=fake_t)
    assert raw._transport is fake_t


def test_raw_driver_open_close_noop_when_external_transport():
    fake_t = MagicMock(spec=SharedTransport)
    fake_t._ser = MagicMock()  # pretend it's open
    raw = RawDriver(addr=1, transport=fake_t)
    raw.open()
    raw.close()
    # The bus owns the transport: open/close on RawDriver must not propagate.
    fake_t.open.assert_not_called()
    fake_t.close.assert_not_called()


def test_raw_driver_internal_transport_when_none():
    raw = RawDriver(port="/dev/foo", baud=38400, addr=1, timeout=1.0)
    # Either the transport stays None until open(), or it's a SharedTransport
    # that's not yet opened.
    assert raw._transport is None or isinstance(raw._transport, SharedTransport)


def test_raw_driver_txn_calls_transport_transact():
    fake_t = MagicMock(spec=SharedTransport)
    fake_t._ser = MagicMock()  # truthy => "open"
    fake_t.transact.return_value = (1, 0x30, b"\xab\xcd")
    raw = RawDriver(addr=1, transport=fake_t)
    raw.open()  # noop with external transport
    payload = raw._txn(0x30, b"", expect_payload_len=2)
    assert payload == b"\xab\xcd"
    fake_t.transact.assert_called_once()


def test_raw_driver_internal_transport_opens_on_open():
    """RawDriver with no external transport creates and opens an internal one."""
    from unittest.mock import patch
    raw = RawDriver(port="/dev/foo", baud=38400, addr=1, timeout=1.0)
    with patch("mks_servo.transport.serial.Serial") as fake_serial_cls:
        raw.open()
        # An internal SharedTransport was created and opened.
        assert raw._transport is not None
        assert raw._transport._ser is not None
        fake_serial_cls.assert_called_once()
