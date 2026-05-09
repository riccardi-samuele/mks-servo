import pytest
from mks_servo.motor import Motor
from mks_servo.raw import MotorStatus

# MotorStatus members that represent "in motion":
#   SPEED_UP, SPEED_DOWN, FULL_SPEED, HOMING, CALIBRATING
# "Not moving": STOPPED, QUERY_FAIL

_MOVING_STATUSES = (
    MotorStatus.SPEED_UP,
    MotorStatus.SPEED_DOWN,
    MotorStatus.FULL_SPEED,
    MotorStatus.HOMING,
)


def test_read_converts_counts_to_degrees(base_profile, mock_raw):
    mock_raw.read_encoder_addition.return_value = 4096   # quarter rev
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert abs(m.read() - 90.0) < 1e-6


def test_read_applies_gear_ratio(base_profile, mock_raw):
    base_profile.mechanical.gear_ratio = 2.0
    mock_raw.read_encoder_addition.return_value = 4096   # motor 90° → output 45°
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert abs(m.read() - 45.0) < 1e-6


def test_read_subtracts_origin_offset(base_profile, mock_raw):
    base_profile.origin.encoder_offset_counts = 1000
    mock_raw.read_encoder_addition.return_value = 4096 + 1000
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert abs(m.read() - 90.0) < 1e-6


def test_error_returns_angle_error_in_degrees(base_profile, mock_raw):
    # firmware returns angle error in driver units (51200 = 360°)
    # 512 units = 3.6° exactly
    mock_raw.read_angle_error.return_value = 512
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert abs(m.error() - 3.6) < 1e-6


def test_error_applies_gear_ratio(base_profile, mock_raw):
    # With gear_ratio=2, output-axis error is halved
    base_profile.mechanical.gear_ratio = 2.0
    mock_raw.read_angle_error.return_value = 512   # motor 3.6° → output 1.8°
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert abs(m.error() - 1.8) < 1e-6


@pytest.mark.parametrize("status", _MOVING_STATUSES)
def test_is_moving_true_for_motion_states(base_profile, mock_raw, status):
    mock_raw.read_motor_status.return_value = status
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.is_moving() is True


def test_is_moving_false_when_stopped(base_profile, mock_raw):
    mock_raw.read_motor_status.return_value = MotorStatus.STOPPED
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.is_moving() is False


def test_is_moving_returns_bool(base_profile, mock_raw):
    mock_raw.read_motor_status.return_value = MotorStatus.FULL_SPEED
    m = Motor(base_profile, raw=mock_raw); m.attach()
    result = m.is_moving()
    assert type(result) is bool


def test_emergency_stop_calls_stop_then_disable(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.emergency_stop()
    mock_raw.emergency_stop.assert_called_once()
    mock_raw.enable.assert_called_with(False)


def test_emergency_stop_swallows_exceptions(base_profile, mock_raw):
    mock_raw.emergency_stop.side_effect = RuntimeError("boom")
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.emergency_stop()  # no exception raised


def test_emergency_stop_safe_when_not_attached(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    # Not attached: must still be safe to call (best-effort signal handler use case).
    m.emergency_stop()  # should not raise
