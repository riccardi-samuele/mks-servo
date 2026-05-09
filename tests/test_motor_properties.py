import pytest
from mks_servo.motor import Motor
from mks_servo.constants import Direction
from mks_servo.exceptions import MotorNotAttached


def test_microsteps_setter_calls_raw(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    mock_raw.set_subdivision.reset_mock()
    m.microsteps = 32
    mock_raw.set_subdivision.assert_called_with(32)
    assert m.profile.config.microsteps == 32


def test_microsteps_getter(base_profile, mock_raw):
    base_profile.config.microsteps = 64
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.microsteps == 64


def test_microsteps_out_of_range_raises(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    with pytest.raises(ValueError):
        m.microsteps = 999
    with pytest.raises(ValueError):
        m.microsteps = 0


def test_microsteps_before_attach_raises(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    with pytest.raises(MotorNotAttached):
        m.microsteps = 16


def test_direction_setter_calls_raw(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.direction = Direction.CCW
    mock_raw.set_direction.assert_called_with(Direction.CCW)
    assert m.profile.config.direction == Direction.CCW


def test_direction_getter(base_profile, mock_raw):
    base_profile.config.direction = Direction.CW
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.direction == Direction.CW


def test_hold_current_pct_setter(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.hold_current_pct = 30
    # RawDriver.set_hold_current_pct accepts the percent (10..90 step 10).
    mock_raw.set_hold_current_pct.assert_called_with(30)
    assert m.profile.config.hold_current_pct == 30


def test_hold_current_pct_getter(base_profile, mock_raw):
    base_profile.config.hold_current_pct = 70
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.hold_current_pct == 70


def test_hold_current_pct_invalid_raises(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    with pytest.raises(ValueError):
        m.hold_current_pct = 55  # not multiple of 10
    with pytest.raises(ValueError):
        m.hold_current_pct = 100  # > 90
    with pytest.raises(ValueError):
        m.hold_current_pct = 5    # < 10
