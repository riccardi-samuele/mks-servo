from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from mks_servo.cli.__main__ import cli
from mks_servo.constants import WorkMode, Direction


def _fake_raw_with_config():
    """A MagicMock that pretends to be a RawDriver with a working read_all_config."""
    fake_raw = MagicMock()
    fake_raw.read_all_config.return_value = {
        "mode": WorkMode.SR_vFOC,
        "current_ma": 1500,
        "hold_current_pct_idx": 4,  # index 4 → 50%
        "subdivision": 16,
        "dir_cw": True,
        "slave_addr": 1,
        "baud_code": 0x04,  # 38400 baud code
    }
    return fake_raw


def test_from_driver_creates_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_raw = _fake_raw_with_config()
    with patch("mks_servo.cli.profile_cmds.RawDriver", return_value=fake_raw):
        res = CliRunner().invoke(cli, [
            "profile", "from-driver",
            "--port", "/dev/ttyUSB0", "--addr", "1", "--as", "wrist",
        ])
    assert res.exit_code == 0, res.output
    out = tmp_path / "profiles" / "wrist.yaml"
    assert out.exists()
    text = out.read_text()
    assert "id: wrist" in text


def test_from_driver_sets_port_in_profile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_raw = _fake_raw_with_config()
    with patch("mks_servo.cli.profile_cmds.RawDriver", return_value=fake_raw):
        res = CliRunner().invoke(cli, [
            "profile", "from-driver",
            "--port", "/dev/ttyUSB1", "--addr", "1", "--as", "wrist",
        ])
    assert res.exit_code == 0, res.output
    text = (tmp_path / "profiles" / "wrist.yaml").read_text()
    assert "/dev/ttyUSB1" in text


def test_from_driver_refuses_overwrite_without_force(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "profiles").mkdir()
    (tmp_path / "profiles" / "wrist.yaml").write_text("# existing\n")
    fake_raw = _fake_raw_with_config()
    with patch("mks_servo.cli.profile_cmds.RawDriver", return_value=fake_raw):
        res = CliRunner().invoke(cli, [
            "profile", "from-driver",
            "--port", "/dev/ttyUSB0", "--addr", "1", "--as", "wrist",
        ])
    assert res.exit_code != 0
    assert "exists" in res.output.lower()


def test_from_driver_force_overwrites(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "profiles").mkdir()
    (tmp_path / "profiles" / "wrist.yaml").write_text("# existing\n")
    fake_raw = _fake_raw_with_config()
    with patch("mks_servo.cli.profile_cmds.RawDriver", return_value=fake_raw):
        res = CliRunner().invoke(cli, [
            "profile", "from-driver",
            "--port", "/dev/ttyUSB0", "--addr", "1", "--as", "wrist", "--force",
        ])
    assert res.exit_code == 0, res.output


def test_from_driver_closes_connection(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_raw = _fake_raw_with_config()
    with patch("mks_servo.cli.profile_cmds.RawDriver", return_value=fake_raw):
        res = CliRunner().invoke(cli, [
            "profile", "from-driver",
            "--port", "/dev/ttyUSB0", "--addr", "1", "--as", "wrist",
        ])
    assert res.exit_code == 0
    fake_raw.close.assert_called_once()
