from unittest.mock import MagicMock
import pytest
from mks_servo.transport import transact
from mks_servo.exceptions import CommTimeout


def test_transact_writes_frame_and_reads_response():
    ser = MagicMock()
    ser.read.side_effect = [b"\xfb\x01", b"\x30\x00\x00\x40\x00", b"\x6c"]
    ser.in_waiting = 0
    addr, code, payload = transact(ser, addr=1, code=0x30, data=b"",
                                   expect_payload_len=4, timeout=1.0)
    assert addr == 1
    assert code == 0x30
    assert payload == b"\x00\x00\x40\x00"
    ser.write.assert_called_once()


def test_transact_raises_commtimeout_on_short_read():
    ser = MagicMock()
    ser.read.return_value = b""
    with pytest.raises(CommTimeout):
        transact(ser, addr=1, code=0x30, data=b"",
                 expect_payload_len=4, timeout=0.01)


from unittest.mock import patch
from mks_servo.transport import SharedTransport


def test_shared_transport_open_creates_serial(monkeypatch):
    fake_serial_cls = MagicMock()
    fake_serial = MagicMock()
    fake_serial_cls.return_value = fake_serial
    monkeypatch.setattr("mks_servo.transport.serial.Serial", fake_serial_cls)
    t = SharedTransport(port="/dev/foo", baud=38400, timeout=2.0)
    t.open()
    fake_serial_cls.assert_called_once_with(
        port="/dev/foo", baudrate=38400, bytesize=8, parity="N",
        stopbits=1, timeout=2.0,
    )


def test_shared_transport_close_idempotent(monkeypatch):
    monkeypatch.setattr("mks_servo.transport.serial.Serial", MagicMock())
    t = SharedTransport(port="/dev/foo")
    t.open()
    t.close()
    t.close()  # should not raise


def test_shared_transport_context_manager(monkeypatch):
    fake_serial = MagicMock()
    monkeypatch.setattr("mks_servo.transport.serial.Serial",
                        MagicMock(return_value=fake_serial))
    with SharedTransport(port="/dev/foo") as t:
        assert t._ser is fake_serial
    fake_serial.close.assert_called_once()


def test_shared_transport_transact_holds_lock():
    """Verify that transact acquires the lock."""
    import threading
    t = SharedTransport(port="/dev/foo")
    t._ser = MagicMock()
    # Replace the real lock with a spy that wraps it
    real_lock = threading.Lock()
    order = []
    spy_lock = MagicMock(wraps=real_lock)
    spy_lock.__enter__ = MagicMock(side_effect=lambda: order.append("acquire") or real_lock.acquire())
    spy_lock.__exit__ = MagicMock(side_effect=lambda *a: real_lock.release())
    t._lock = spy_lock
    with patch("mks_servo.transport.transact",
               return_value=(1, 0x30, b"")) as fake_module_transact:
        t.transact(addr=1, code=0x30, data=b"", expect_payload_len=0, timeout=0.1)
        assert "acquire" in order
        fake_module_transact.assert_called_once()
