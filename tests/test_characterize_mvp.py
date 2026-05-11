from unittest.mock import MagicMock, PropertyMock
import pytest
from mks_servo.characterize import CharacterizationSuite, SuiteResult
from mks_servo.profile import Profile, DriverSection


def _stub_time(monkeypatch, step=0.01):
    monkeypatch.setattr("mks_servo.characterize._time.sleep", lambda *_: None)
    state = [0.0]
    def fake():
        state[0] += step
        return state[0]
    monkeypatch.setattr("mks_servo.characterize._time.monotonic", fake)


def _fake_motor():
    m = MagicMock()
    m.read.return_value = 0.0
    m.error.return_value = 0.1
    type(m).speed_rpm = PropertyMock(return_value=2000)
    m.profile = Profile(id="t", driver=DriverSection(model="servo42d", slave_addr=1))
    return m


def test_run_mvp_returns_full_suiteresult(monkeypatch):
    _stub_time(monkeypatch)
    m = _fake_motor()
    suite = CharacterizationSuite(m)
    res = suite.run_mvp()
    assert isinstance(res, SuiteResult)
    assert res.p1 is not None
    assert res.p3 is not None
    assert res.p5 is not None
    assert res.s2 is not None


def test_run_full_alias_runs_mvp(monkeypatch):
    _stub_time(monkeypatch)
    m = _fake_motor()
    suite = CharacterizationSuite(m)
    res = suite.run_full()
    assert isinstance(res, SuiteResult)
    assert res.p1 is not None


def test_update_profile_writes_p1_and_s2(monkeypatch):
    _stub_time(monkeypatch)
    m = _fake_motor()
    suite = CharacterizationSuite(m)
    suite.run_mvp()
    suite.update_profile()
    assert m.profile.characterization.precision.sigma_deg is not None
    assert m.profile.characterization.precision.peak_deg is not None
    assert m.profile.characterization.speed.max_measured_rpm is not None


def test_update_profile_does_not_touch_unrelated_fields(monkeypatch):
    _stub_time(monkeypatch)
    m = _fake_motor()
    m.profile.mechanical.gear_ratio = 2.5
    m.profile.limits.position.min_deg = -90.0
    suite = CharacterizationSuite(m)
    suite.run_mvp()
    suite.update_profile()
    assert m.profile.mechanical.gear_ratio == 2.5
    assert m.profile.limits.position.min_deg == -90.0


def test_update_profile_no_results_is_safe():
    """Calling update_profile with no prior run is a no-op."""
    m = MagicMock()
    m.profile = Profile(id="t", driver=DriverSection(model="servo42d", slave_addr=1))
    suite = CharacterizationSuite(m)
    suite.update_profile()  # should not raise
    # Profile fields stay at defaults (None)
    assert m.profile.characterization.precision.sigma_deg is None
