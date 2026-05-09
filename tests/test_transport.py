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
