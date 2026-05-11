"""HIL: CharacterizationSuite against real hardware. Requires the rig.
Sub-tests are run with reduced parameters for speed; the final test runs the
full run_mvp() with defaults as an end-to-end integration check."""
import math
import time as _time
import pytest

from mks_servo import Motor
from mks_servo.characterize import (
    CharacterizationSuite, P1Result, P3Result, P5Result, S2Result, SuiteResult,
)

pytestmark = pytest.mark.hil


def _stop_and_settle(m):
    """Instant stop (acc=0) + a short pause so the next test's attach() doesn't
    hit a still-coasting driver."""
    try:
        m.raw.move_speed(rpm=0, acc=0)
    except Exception:
        pass
    _time.sleep(0.3)


def test_p1_precision_returns_well_formed_result(hil_profile):
    with Motor(hil_profile) as m:
        m.set_origin()
        suite = CharacterizationSuite(m)
        res = suite.run_p1_precision(target_deg=0.0, iterations=3, rpm=300)
        assert isinstance(res, P1Result)
        assert res.iterations == 3
        assert len(res.samples_deg) == 3
        assert all(isinstance(s, float) for s in res.samples_deg)
        assert res.sigma_deg >= 0.0
        assert res.peak_deg >= 0.0
        assert not math.isnan(res.mean_deg)
        # The motor should land near the target each time.
        assert res.peak_deg < 2.0, f"P1 peak deviation too large: {res.peak_deg}°"
        assert suite._last_results.p1 is res


def test_p3_error_vs_rpm_returns_well_formed_result(hil_profile):
    with Motor(hil_profile) as m:
        m.set_origin()
        suite = CharacterizationSuite(m)
        res = suite.run_p3_error_vs_rpm(rpms=[100, 500], samples_per_rpm=2,
                                        target_deg=90.0)
        assert isinstance(res, P3Result)
        assert res.rpm_samples == [100, 500]
        assert len(res.rms_error_deg) == 2
        assert all(v >= 0.0 and not math.isnan(v) for v in res.rms_error_deg)
        m.write(0)


def test_p5_follow_error_returns_well_formed_result(hil_profile):
    with Motor(hil_profile) as m:
        m.set_origin()
        suite = CharacterizationSuite(m)
        res = suite.run_p5_follow_error(rpm=60, duration_s=1.0, sweep_deg=180.0,
                                        sample_interval_s=0.05)
        assert isinstance(res, P5Result)
        assert res.rpm == 60
        assert res.max_follow_err_deg >= 0.0
        assert res.rms_follow_err_deg >= 0.0
        assert not math.isnan(res.rms_follow_err_deg)
        m.write(0)


def test_s2_acceleration_returns_well_formed_result(hil_profile):
    with Motor(hil_profile) as m:
        suite = CharacterizationSuite(m)
        # Wide sampling window (≈2 s) so even a slow ramp gets meaningfully
        # above zero; small acc values so we definitely see motion.
        res = suite.run_s2_acceleration(target_rpm=600, accs=[2, 50],
                                        samples_per_acc=200,
                                        sample_interval_s=0.01, cool_s=0.5)
        assert isinstance(res, S2Result)
        assert res.target_rpm == 600
        assert res.accs == [2, 50]
        assert len(res.time_to_target_ms) == 2
        # Each entry is either None (never reached 95%) or a non-negative float.
        for t in res.time_to_target_ms:
            assert t is None or (isinstance(t, float) and t >= 0.0)
        # The motor should have actually spun and we should have sampled it.
        assert res.max_observed_rpm > 50, \
            f"S2 saw max RPM {res.max_observed_rpm}; expected the motor to spin"
        _stop_and_settle(m)


def test_update_profile_writes_characterization_fields(hil_profile):
    with Motor(hil_profile) as m:
        m.set_origin()
        suite = CharacterizationSuite(m)
        suite.run_p1_precision(target_deg=0.0, iterations=3, rpm=300)
        suite.run_s2_acceleration(target_rpm=600, accs=[50],
                                  samples_per_acc=120, cool_s=0.5)
        suite.update_profile()
        char = m.profile.characterization
        assert char.precision.sigma_deg == suite._last_results.p1.sigma_deg
        assert char.precision.peak_deg == suite._last_results.p1.peak_deg
        assert char.speed.max_measured_rpm == suite._last_results.s2.max_observed_rpm
        _stop_and_settle(m)


def test_run_mvp_end_to_end(hil_profile):
    """Full run_mvp() with default parameters — the real integration check.
    Note: defaults ramp toward 2000 RPM (above this rig's ~1350 RPM ceiling at
    12 V) with a ~0.5 s sampling window, so S2 time-to-target entries are
    expected to be None; that's fine — this test only checks the suite runs
    end-to-end and returns well-formed results."""
    with Motor(hil_profile) as m:
        m.set_origin()
        suite = CharacterizationSuite(m)
        results = suite.run_mvp()
        assert isinstance(results, SuiteResult)
        assert results.p1 is not None and isinstance(results.p1, P1Result)
        assert results.p3 is not None and isinstance(results.p3, P3Result)
        assert results.p5 is not None and isinstance(results.p5, P5Result)
        assert results.s2 is not None and isinstance(results.s2, S2Result)
        # Sanity on the headline numbers.
        assert results.p1.sigma_deg >= 0.0 and results.p1.peak_deg < 3.0
        assert results.s2.max_observed_rpm >= 0
        # update_profile() must accept the results without error.
        suite.update_profile()
        m.write(0)
        _stop_and_settle(m)
