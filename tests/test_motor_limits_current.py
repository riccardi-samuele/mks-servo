import pytest
from mks_servo.motor import Motor
from mks_servo.exceptions import LimitExceeded, MotorNotAttached


def test_set_current_within_max_writes_to_driver(base_profile, mock_raw):
    base_profile.limits.current.max_ma = 2500
    m = Motor(base_profile, raw=mock_raw); m.attach()
    mock_raw.set_work_current_ma.reset_mock()
    m.work_current_ma = 2000
    mock_raw.set_work_current_ma.assert_called_with(2000)
    assert m.profile.config.work_current_ma == 2000


def test_set_current_above_max_always_rejects(base_profile, mock_raw):
    base_profile.limits.current.max_ma = 2500
    m = Motor(base_profile, raw=mock_raw); m.attach()
    with pytest.raises(LimitExceeded) as exc:
        m.work_current_ma = 3000
    assert exc.value.kind == "current"
    assert exc.value.value == 3000
    assert exc.value.limit == 2500


def test_set_current_zero_allowed(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.work_current_ma = 0
    mock_raw.set_work_current_ma.assert_called_with(0)


def test_set_current_negative_rejects(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    with pytest.raises(LimitExceeded):
        m.work_current_ma = -100


def test_get_current_returns_profile_value(base_profile, mock_raw):
    base_profile.config.work_current_ma = 1700
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.work_current_ma == 1700


def test_set_current_before_attach_raises(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    with pytest.raises(MotorNotAttached):
        m.work_current_ma = 1000
