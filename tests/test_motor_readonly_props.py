import pytest
from mks_servo.motor import Motor
from mks_servo.raw import MotorStatus
from mks_servo.exceptions import LimitExceeded


def test_position_counts(base_profile, mock_raw):
    mock_raw.read_encoder_addition.return_value = 12345
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.position_counts == 12345


def test_speed_rpm(base_profile, mock_raw):
    mock_raw.read_speed_rpm.return_value = -500
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.speed_rpm == -500


def test_status(base_profile, mock_raw):
    mock_raw.read_motor_status.return_value = MotorStatus.SPEED_UP
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.status == MotorStatus.SPEED_UP


def test_position_limits_runtime_override_used_for_check(base_profile, mock_raw):
    base_profile.limits.position.min_deg = -180
    base_profile.limits.position.max_deg = 180
    base_profile.limits.position.on_violation = "reject"
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.position_limits = (-45, 45)
    with pytest.raises(LimitExceeded):
        m.write(90, blocking=False)


def test_position_limits_disable(base_profile, mock_raw):
    base_profile.limits.position.min_deg = -90
    base_profile.limits.position.max_deg = 90
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.position_limits = (None, None)
    m.write(1000, blocking=False)  # no exception
    mock_raw.move_absolute_axis.assert_called_once()


def test_position_limits_invalid_value_raises(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    with pytest.raises(ValueError):
        m.position_limits = "not a tuple"


def test_speed_limit_rpm_override(base_profile, mock_raw):
    base_profile.limits.speed.max_rpm_safe = 5000
    base_profile.limits.speed.on_violation = "clamp"
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.speed_limit_rpm = 500
    m.write(0, rpm=2000, blocking=False)
    args, kwargs = mock_raw.move_absolute_axis.call_args
    rpm = kwargs.get("rpm", args[1])
    assert rpm == 500


def test_speed_limit_rpm_setter_accepts_none(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.speed_limit_rpm = None
    assert m.speed_limit_rpm is None


def test_position_limits_getter(base_profile, mock_raw):
    base_profile.limits.position.min_deg = -90
    base_profile.limits.position.max_deg = 90
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.position_limits == (-90, 90)
    m.position_limits = (-45, 45)
    assert m.position_limits == (-45, 45)
