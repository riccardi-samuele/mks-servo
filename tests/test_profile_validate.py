import pytest
from mks_servo.profile import (
    Profile, DriverSection, ConfigSection, LimitsSection,
    PositionLimit, SpeedLimit, CurrentLimit, MechanicalSection,
)
from mks_servo.constants import WorkMode, Direction
from mks_servo.exceptions import ProfileError


def _ok():
    return Profile(id="wrist", driver=DriverSection(model="servo42d", slave_addr=1))


def test_valid_profile_passes():
    _ok().validate()  # no exception


def test_id_must_be_safe():
    p = _ok(); p.id = "a b"
    with pytest.raises(ProfileError) as exc:
        p.validate()
    assert any("id" in v for v in exc.value.violations)


def test_unknown_driver_model():
    p = _ok(); p.driver.model = "smoothieboard"
    with pytest.raises(ProfileError):
        p.validate()


def test_slave_addr_out_of_range():
    p = _ok(); p.driver.slave_addr = 300
    with pytest.raises(ProfileError):
        p.validate()


def test_microsteps_out_of_range():
    p = _ok(); p.config.microsteps = 999
    with pytest.raises(ProfileError):
        p.validate()


def test_hold_current_pct_must_be_step_of_10():
    p = _ok(); p.config.hold_current_pct = 55
    with pytest.raises(ProfileError):
        p.validate()


def test_position_limits_partial_must_match():
    p = _ok(); p.limits.position.min_deg = -90.0; p.limits.position.max_deg = None
    with pytest.raises(ProfileError):
        p.validate()


def test_position_limits_min_must_be_less_than_max():
    p = _ok(); p.limits.position.min_deg = 90.0; p.limits.position.max_deg = -90.0
    with pytest.raises(ProfileError):
        p.validate()


def test_gear_ratio_must_be_positive():
    p = _ok(); p.mechanical.gear_ratio = 0.0
    with pytest.raises(ProfileError):
        p.validate()


def test_violations_collected_not_failfast():
    p = _ok()
    p.id = "a b"
    p.driver.slave_addr = 999
    p.config.microsteps = 999
    with pytest.raises(ProfileError) as exc:
        p.validate()
    assert len(exc.value.violations) >= 3
