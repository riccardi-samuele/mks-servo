import pytest
from mks_servo.exceptions import (
    MKSError,
    CommTimeout,
    ChecksumError,
    ProtocolError,
    MotorFault,
    CalibrationFailed,
)


def test_all_inherit_from_mkserror():
    for cls in (CommTimeout, ChecksumError, ProtocolError, MotorFault, CalibrationFailed):
        assert issubclass(cls, MKSError)


def test_mkserror_inherits_from_exception():
    assert issubclass(MKSError, Exception)


def test_can_raise_and_catch():
    with pytest.raises(MKSError):
        raise CommTimeout("no response")
