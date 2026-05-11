from unittest.mock import MagicMock
import pytest
from mks_servo.characterize import CharacterizationSuite


def _fake_motor_with_reads(read_values):
    m = MagicMock()
    m.read.side_effect = list(read_values)
    return m


def test_run_p1_precision_computes_sigma_and_peak():
    m = _fake_motor_with_reads([0.0, 0.5, -0.4, 0.1, 0.0])
    suite = CharacterizationSuite(m)
    res = suite.run_p1_precision(target_deg=0.0, iterations=5)
    assert res.iterations == 5
    assert res.samples_deg == [0.0, 0.5, -0.4, 0.1, 0.0]
    assert res.peak_deg == pytest.approx(0.5)
    assert res.mean_deg == pytest.approx(0.04)
    assert res.sigma_deg > 0
    assert suite._last_results.p1 is res


def test_run_p1_calls_write_iterations_times():
    m = MagicMock()
    m.read.side_effect = [0.1, 0.2, 0.0]
    suite = CharacterizationSuite(m)
    suite.run_p1_precision(target_deg=0.0, iterations=3, rpm=300)
    assert m.write.call_count == 3


def test_run_p1_uses_default_target_zero():
    m = _fake_motor_with_reads([0.0, 0.0, 0.0])
    suite = CharacterizationSuite(m)
    res = suite.run_p1_precision(iterations=3)
    assert res.target_deg == 0.0


def test_run_p3_error_vs_rpm_default_rpms():
    # 5 default rpms × 5 samples = 25 reads
    reads = [0.1, -0.1, 0.05, 0.0, -0.05] * 5
    m = _fake_motor_with_reads(reads)
    suite = CharacterizationSuite(m)
    res = suite.run_p3_error_vs_rpm(samples_per_rpm=5)
    assert res.rpm_samples == [50, 100, 300, 500, 1000]
    assert len(res.rms_error_deg) == 5
    for v in res.rms_error_deg:
        assert v >= 0
    assert suite._last_results.p3 is res


def test_run_p3_custom_rpms_and_samples():
    # 3 rpms × 4 samples = 12 reads
    reads = [0.1, 0.0, -0.05, 0.0] * 3
    m = _fake_motor_with_reads(reads)
    suite = CharacterizationSuite(m)
    res = suite.run_p3_error_vs_rpm(rpms=[100, 300, 500], samples_per_rpm=4)
    assert res.rpm_samples == [100, 300, 500]
    assert len(res.rms_error_deg) == 3


def test_run_p3_writes_target_for_each_rpm():
    m = MagicMock()
    m.read.return_value = 0.0
    suite = CharacterizationSuite(m)
    suite.run_p3_error_vs_rpm(rpms=[100, 200], samples_per_rpm=2)
    # 2 rpms × 2 samples = 4 writes
    assert m.write.call_count == 4
