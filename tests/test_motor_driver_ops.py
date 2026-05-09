"""Tests for Motor.restart() and Motor.restore_defaults()."""
import pytest
from mks_servo.motor import Motor
from mks_servo.exceptions import MotorNotAttached


def test_restart_calls_raw_restart_then_reapplies_config(base_profile, mock_raw, monkeypatch):
    monkeypatch.setattr("mks_servo.motor._time.sleep", lambda *_: None)
    m = Motor(base_profile, raw=mock_raw); m.attach()
    mock_raw.reset_mock()
    m.restart()
    mock_raw.restart.assert_called_once()
    mock_raw.set_work_mode.assert_called_once_with(base_profile.config.mode)
    mock_raw.set_subdivision.assert_called_once_with(base_profile.config.microsteps)
    mock_raw.set_work_current_ma.assert_called_once_with(base_profile.config.work_current_ma)


def test_restore_defaults_calls_raw(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.restore_defaults()
    mock_raw.restore_defaults.assert_called_once()


def test_restart_before_attach_raises(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    with pytest.raises(MotorNotAttached):
        m.restart()


def test_restore_defaults_before_attach_raises(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    with pytest.raises(MotorNotAttached):
        m.restore_defaults()
