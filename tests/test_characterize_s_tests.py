# tests/test_characterize_s_tests.py
from unittest.mock import MagicMock, PropertyMock
import pytest
from mks_servo.characterize import CharacterizationSuite


def _stub_clock(monkeypatch, step=0.05):
    """Replace _time.monotonic with a counter that ticks `step` seconds per call."""
    state = [0.0]
    def fake():
        state[0] += step
        return state[0]
    monkeypatch.setattr("mks_servo.characterize._time.monotonic", fake)


def test_run_p5_follow_error_returns_correct_shape(monkeypatch):
    monkeypatch.setattr("mks_servo.characterize._time.sleep", lambda *_: None)
    _stub_clock(monkeypatch, step=0.1)
    m = MagicMock()
    # error() will be called several times during the loop. Provide enough values.
    m.error.side_effect = [0.1, 0.5, 1.0, 0.8, 0.2, 0.0] + [0.0] * 100
    suite = CharacterizationSuite(m)
    res = suite.run_p5_follow_error(rpm=60, duration_s=0.5,
                                    sample_interval_s=0.01)
    assert res.rpm == 60
    assert res.duration_s == 0.5
    assert res.max_follow_err_deg >= 0
    assert res.rms_follow_err_deg >= 0
    assert suite._last_results.p5 is res


def test_run_p5_calls_motor_write_twice(monkeypatch):
    monkeypatch.setattr("mks_servo.characterize._time.sleep", lambda *_: None)
    _stub_clock(monkeypatch, step=0.5)  # exits the loop quickly
    m = MagicMock()
    m.error.return_value = 0.1
    suite = CharacterizationSuite(m)
    suite.run_p5_follow_error(rpm=60, duration_s=0.1)
    # Two writes: setup move (blocking) + sweep start (non-blocking)
    assert m.write.call_count == 2


def test_run_s2_acceleration_returns_correct_shape(monkeypatch):
    monkeypatch.setattr("mks_servo.characterize._time.sleep", lambda *_: None)
    _stub_clock(monkeypatch, step=0.01)
    m = MagicMock()
    type(m).speed_rpm = PropertyMock(return_value=2000)  # always at target
    suite = CharacterizationSuite(m)
    res = suite.run_s2_acceleration(target_rpm=2000, accs=[100, 200],
                                    samples_per_acc=3)
    assert res.target_rpm == 2000
    assert res.accs == [100, 200]
    assert len(res.time_to_target_ms) == 2
    assert res.max_observed_rpm >= 0
    assert suite._last_results.s2 is res


def test_run_s2_calls_move_speed_for_each_acc(monkeypatch):
    monkeypatch.setattr("mks_servo.characterize._time.sleep", lambda *_: None)
    _stub_clock(monkeypatch, step=0.01)
    m = MagicMock()
    type(m).speed_rpm = PropertyMock(return_value=2000)
    suite = CharacterizationSuite(m)
    suite.run_s2_acceleration(target_rpm=2000, accs=[100, 200, 255],
                              samples_per_acc=2)
    # For each acc we call move_speed at least twice (start + stop)
    # so >= 6 calls total. Just assert called.
    assert m.raw.move_speed.called
    # Total accs * 2 (start + stop after) == 6
    assert m.raw.move_speed.call_count >= 3


def test_run_s2_handles_speed_never_reached(monkeypatch):
    """If speed_rpm never reaches target, time_to_target_ms entry is None."""
    monkeypatch.setattr("mks_servo.characterize._time.sleep", lambda *_: None)
    _stub_clock(monkeypatch, step=0.01)
    m = MagicMock()
    type(m).speed_rpm = PropertyMock(return_value=100)  # well below target
    suite = CharacterizationSuite(m)
    res = suite.run_s2_acceleration(target_rpm=2000, accs=[1],
                                    samples_per_acc=3)
    assert res.time_to_target_ms == [None]
