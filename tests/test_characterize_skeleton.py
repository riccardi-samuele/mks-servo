from mks_servo.characterize import (
    CharacterizationSuite, P1Result, P3Result, P5Result, S2Result, SuiteResult,
)


def test_p1_result_dataclass():
    p1 = P1Result(target_deg=0.0, iterations=5,
                  samples_deg=[0.0, 0.1, -0.1, 0.0, 0.05],
                  mean_deg=0.01, sigma_deg=0.07, peak_deg=0.1)
    assert p1.iterations == 5
    assert p1.target_deg == 0.0


def test_p3_result_dataclass():
    p3 = P3Result(rpm_samples=[100, 300], rms_error_deg=[0.1, 0.05])
    assert len(p3.rpm_samples) == 2


def test_p5_result_dataclass():
    p5 = P5Result(rpm=60, duration_s=2.0,
                  max_follow_err_deg=1.2, rms_follow_err_deg=0.5)
    assert p5.rpm == 60


def test_s2_result_dataclass():
    s2 = S2Result(target_rpm=2000, accs=[1, 50],
                  time_to_target_ms=[5000.0, 100.0], max_observed_rpm=1900)
    assert s2.max_observed_rpm == 1900


def test_suite_result_dataclass():
    sr = SuiteResult()
    assert sr.p1 is None
    assert sr.p3 is None


def test_suite_construct():
    fake_motor = object()
    suite = CharacterizationSuite(fake_motor)
    assert suite._motor is fake_motor
    assert suite._last_results.p1 is None
    assert suite._output_dir is None


def test_suite_construct_with_output_dir(tmp_path):
    fake_motor = object()
    suite = CharacterizationSuite(fake_motor, output_dir=tmp_path)
    assert suite._output_dir == tmp_path
