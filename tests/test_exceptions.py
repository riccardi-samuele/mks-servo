import pytest
from mks_servo.exceptions import (
    MKSError,
    CommTimeout,
    ChecksumError,
    ProtocolError,
    MotorFault,
    CalibrationFailed,
    ProfileError,
    LimitExceeded,
    MotorNotAttached,
)


def test_all_inherit_from_mkserror():
    for cls in (CommTimeout, ChecksumError, ProtocolError, MotorFault, CalibrationFailed):
        assert issubclass(cls, MKSError)


def test_mkserror_inherits_from_exception():
    assert issubclass(MKSError, Exception)


def test_can_raise_and_catch():
    with pytest.raises(MKSError):
        raise CommTimeout("no response")


def test_profile_error_carries_violations_list():
    err = ProfileError("invalid", violations=["bad mode", "bad current"])
    assert err.violations == ["bad mode", "bad current"]
    assert isinstance(err, MKSError)


def test_profile_error_without_violations():
    err = ProfileError("just a message")
    assert err.violations == []


def test_limit_exceeded_carries_kind_value_limit():
    err = LimitExceeded(kind="position", value=200.0, limit=180.0)
    assert err.kind == "position"
    assert err.value == 200.0
    assert err.limit == 180.0
    assert "position" in str(err) and "200" in str(err) and "180" in str(err)


def test_motor_not_attached_is_mks_error():
    assert issubclass(MotorNotAttached, MKSError)
