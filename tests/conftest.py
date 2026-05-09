"""Shared fixtures for Motor tests."""
import pytest
from unittest.mock import MagicMock
from mks_servo.profile import Profile, DriverSection
from mks_servo.raw import RawDriver, MotorStatus


@pytest.fixture
def mock_raw():
    raw = MagicMock(spec=RawDriver)
    raw.read_motor_status.return_value = MotorStatus.STOPPED
    raw.read_encoder_addition.return_value = 0
    raw.read_speed_rpm.return_value = 0
    raw.read_angle_error.return_value = 0
    return raw


@pytest.fixture
def base_profile():
    return Profile(id="testmotor", driver=DriverSection(model="servo42d", slave_addr=1))
