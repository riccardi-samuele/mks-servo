import pytest
from mks_servo.motor import Motor
from mks_servo.constants import WorkMode


def test_mode_getter_returns_profile_value(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.mode == base_profile.config.mode


def test_mode_setter_calls_set_work_mode_and_restart(base_profile, mock_raw, monkeypatch):
    monkeypatch.setattr("mks_servo.motor._time.sleep", lambda *_: None)
    base_profile.config.mode = WorkMode.SR_OPEN
    m = Motor(base_profile, raw=mock_raw); m.attach()
    mock_raw.reset_mock()
    m.mode = WorkMode.SR_vFOC
    mock_raw.set_work_mode.assert_called_with(WorkMode.SR_vFOC)
    mock_raw.restart.assert_called_once()
    assert m.profile.config.mode == WorkMode.SR_vFOC


def test_mode_setter_reapplies_config_after_restart(base_profile, mock_raw, monkeypatch):
    monkeypatch.setattr("mks_servo.motor._time.sleep", lambda *_: None)
    base_profile.config.microsteps = 32
    base_profile.config.work_current_ma = 1700
    m = Motor(base_profile, raw=mock_raw); m.attach()
    mock_raw.reset_mock()
    m.mode = WorkMode.SR_CLOSE
    # After restart, microsteps and current should be re-asserted on the driver.
    mock_raw.set_subdivision.assert_called_with(32)
    mock_raw.set_work_current_ma.assert_called_with(1700)


def test_mode_before_attach_raises(base_profile, mock_raw):
    from mks_servo.exceptions import MotorNotAttached
    m = Motor(base_profile, raw=mock_raw)
    with pytest.raises(MotorNotAttached):
        m.mode = WorkMode.SR_vFOC
