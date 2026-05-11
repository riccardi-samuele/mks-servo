from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from mks_servo.cli.__main__ import cli
from mks_servo.characterize import (
    SuiteResult, P1Result, P3Result, P5Result, S2Result,
)


def _suite_result():
    return SuiteResult(
        p1=P1Result(target_deg=0.0, iterations=5, samples_deg=[0.0]*5,
                    mean_deg=0.0, sigma_deg=0.05, peak_deg=0.1),
        p3=P3Result(rpm_samples=[100, 300], rms_error_deg=[0.1, 0.05]),
        p5=P5Result(rpm=60, duration_s=2.0, max_follow_err_deg=0.5,
                    rms_follow_err_deg=0.2),
        s2=S2Result(target_rpm=2000, accs=[100, 200],
                    time_to_target_ms=[150, 80], max_observed_rpm=1300),
    )


def test_characterize_invokes_run_mvp_and_prints_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_motor = MagicMock()
    fake_motor.__enter__ = MagicMock(return_value=fake_motor)
    fake_motor.__exit__ = MagicMock(return_value=False)
    fake_suite = MagicMock()
    fake_suite.run_mvp.return_value = _suite_result()
    with patch("mks_servo.cli.characterize_cmds.Motor.from_profile",
               return_value=fake_motor), \
         patch("mks_servo.cli.characterize_cmds.CharacterizationSuite",
               return_value=fake_suite):
        res = CliRunner().invoke(cli, ["characterize", "wrist", "--suite=mvp"])
    assert res.exit_code == 0, res.output
    fake_suite.run_mvp.assert_called_once()
    # Output contains brief summary
    assert "P1" in res.output or "sigma" in res.output.lower()


def test_characterize_full_calls_run_full(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_motor = MagicMock()
    fake_motor.__enter__ = MagicMock(return_value=fake_motor)
    fake_motor.__exit__ = MagicMock(return_value=False)
    fake_suite = MagicMock()
    fake_suite.run_full.return_value = _suite_result()
    with patch("mks_servo.cli.characterize_cmds.Motor.from_profile",
               return_value=fake_motor), \
         patch("mks_servo.cli.characterize_cmds.CharacterizationSuite",
               return_value=fake_suite):
        res = CliRunner().invoke(cli, ["characterize", "wrist", "--suite=full"])
    assert res.exit_code == 0
    fake_suite.run_full.assert_called_once()


def test_characterize_update_profile_calls_update(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_motor = MagicMock()
    fake_motor.__enter__ = MagicMock(return_value=fake_motor)
    fake_motor.__exit__ = MagicMock(return_value=False)
    fake_suite = MagicMock()
    fake_suite.run_mvp.return_value = _suite_result()
    with patch("mks_servo.cli.characterize_cmds.Motor.from_profile",
               return_value=fake_motor), \
         patch("mks_servo.cli.characterize_cmds.CharacterizationSuite",
               return_value=fake_suite):
        res = CliRunner().invoke(cli, ["characterize", "wrist",
                                        "--update-profile"])
    assert res.exit_code == 0
    fake_suite.update_profile.assert_called_once()


def test_characterize_save_calls_profile_save(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_motor = MagicMock()
    fake_motor.__enter__ = MagicMock(return_value=fake_motor)
    fake_motor.__exit__ = MagicMock(return_value=False)
    fake_motor.profile.save = MagicMock()
    fake_suite = MagicMock()
    fake_suite.run_mvp.return_value = _suite_result()
    with patch("mks_servo.cli.characterize_cmds.Motor.from_profile",
               return_value=fake_motor), \
         patch("mks_servo.cli.characterize_cmds.CharacterizationSuite",
               return_value=fake_suite):
        res = CliRunner().invoke(cli, ["characterize", "wrist",
                                        "--update-profile", "--save"])
    assert res.exit_code == 0
    fake_motor.profile.save.assert_called_once()


def test_characterize_save_without_update_warns(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_motor = MagicMock()
    fake_motor.__enter__ = MagicMock(return_value=fake_motor)
    fake_motor.__exit__ = MagicMock(return_value=False)
    fake_suite = MagicMock()
    fake_suite.run_mvp.return_value = _suite_result()
    with patch("mks_servo.cli.characterize_cmds.Motor.from_profile",
               return_value=fake_motor), \
         patch("mks_servo.cli.characterize_cmds.CharacterizationSuite",
               return_value=fake_suite):
        res = CliRunner().invoke(cli, ["characterize", "wrist", "--save"])
    # Exit clean but emits a warning
    assert res.exit_code == 0
    full_output = res.output + (res.stderr if hasattr(res, "stderr") else "")
    assert "warning" in full_output.lower() or "no effect" in full_output.lower()


def test_characterize_passes_port_override(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    captured = {}
    def fake_from_profile(name_or_path, *, port=None):
        captured["port"] = port
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        return m
    fake_suite = MagicMock()
    fake_suite.run_mvp.return_value = _suite_result()
    with patch("mks_servo.cli.characterize_cmds.Motor.from_profile",
               side_effect=fake_from_profile), \
         patch("mks_servo.cli.characterize_cmds.CharacterizationSuite",
               return_value=fake_suite):
        res = CliRunner().invoke(cli, ["characterize", "wrist",
                                        "--port", "/dev/ttyUSB1"])
    assert res.exit_code == 0
    assert captured["port"] == "/dev/ttyUSB1"
