from datetime import datetime
from unittest.mock import call
import pytest
from mks_servo.motor import Motor
from mks_servo.constants import WorkMode
from mks_servo.exceptions import CalibrationFailed
from mks_servo.raw import MotorStatus


def test_calibrate_runs_correct_sequence(base_profile, mock_raw, monkeypatch):
    monkeypatch.setattr("mks_servo.motor._time.sleep", lambda *_: None)
    base_profile.config.work_current_ma = 1500
    # Simulate the polling: CALIBRATING twice then STOPPED.
    mock_raw.read_motor_status.side_effect = [
        MotorStatus.CALIBRATING, MotorStatus.CALIBRATING, MotorStatus.STOPPED,
    ]
    m = Motor(base_profile, raw=mock_raw); m.attach()
    mock_raw.reset_mock()
    # Reset side_effect after reset_mock erases it
    mock_raw.read_motor_status.side_effect = [
        MotorStatus.CALIBRATING, MotorStatus.CALIBRATING, MotorStatus.STOPPED,
    ]
    m.calibrate(current_ma=3000)
    # Assert the disable-before-config pattern:
    mock_raw.enable.assert_any_call(False)
    mock_raw.set_work_mode.assert_called_with(WorkMode.SR_vFOC)
    mock_raw.set_subdivision.assert_called_with(16)
    # set_work_current_ma is called twice: with 3000 (calibration) then with 1500 (restore)
    current_calls = [c.args[0] for c in mock_raw.set_work_current_ma.call_args_list
                     if c.args]
    assert 3000 in current_calls
    assert current_calls[-1] == 1500   # last call restores
    # The actual calibrate opcode was issued
    mock_raw.calibrate.assert_called_once()


def test_calibrate_updates_last_calibrated_on_success(base_profile, mock_raw, monkeypatch):
    monkeypatch.setattr("mks_servo.motor._time.sleep", lambda *_: None)
    mock_raw.read_motor_status.return_value = MotorStatus.STOPPED
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.profile.characterization.last_calibrated is None
    m.calibrate()
    assert isinstance(m.profile.characterization.last_calibrated, datetime)


def test_calibrate_failure_restores_current_and_raises(base_profile, mock_raw, monkeypatch):
    monkeypatch.setattr("mks_servo.motor._time.sleep", lambda *_: None)
    base_profile.config.work_current_ma = 1500
    mock_raw.calibrate.side_effect = CalibrationFailed("driver returned status=2")
    m = Motor(base_profile, raw=mock_raw); m.attach()
    with pytest.raises(CalibrationFailed):
        m.calibrate(current_ma=3000)
    # Current restored to pre-calibration value as the LAST call
    last = mock_raw.set_work_current_ma.call_args_list[-1]
    assert last == call(1500)


def test_calibrate_timeout_raises(base_profile, mock_raw, monkeypatch):
    monkeypatch.setattr("mks_servo.motor._time.sleep", lambda *_: None)
    # Use a fake clock so we exceed timeout immediately
    fake_clock = [0.0]
    def fake_monotonic():
        fake_clock[0] += 100.0  # huge step every call
        return fake_clock[0]
    monkeypatch.setattr("mks_servo.motor._time.monotonic", fake_monotonic)
    mock_raw.read_motor_status.return_value = MotorStatus.CALIBRATING
    m = Motor(base_profile, raw=mock_raw); m.attach()
    with pytest.raises(CalibrationFailed, match="timeout"):
        m.calibrate(timeout=0.001)


def test_calibrate_restores_current_even_if_set_work_current_raises_at_end(
        base_profile, mock_raw, monkeypatch):
    """Restoring current is best-effort — if it fails, calibrate still raises
    its own primary error (or completes if calibration itself succeeded)."""
    monkeypatch.setattr("mks_servo.motor._time.sleep", lambda *_: None)
    mock_raw.read_motor_status.return_value = MotorStatus.STOPPED

    # Calibration itself succeeds, but the restore current fails. The
    # post-success restore-failure should be swallowed.
    base_profile.config.work_current_ma = 1500
    m = Motor(base_profile, raw=mock_raw); m.attach()
    # Set side_effect after attach so _apply_profile_config calls don't count.
    call_count = [0]
    def cur_setter(value):
        call_count[0] += 1
        if call_count[0] == 2:  # the restore call
            raise RuntimeError("driver hiccup")
        return None
    mock_raw.set_work_current_ma.side_effect = cur_setter
    # Should not raise — restore failure is swallowed
    m.calibrate(current_ma=3000)
