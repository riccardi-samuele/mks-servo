from pathlib import Path
from click.testing import CliRunner
from mks_servo.cli.__main__ import cli


def test_from_template_creates_yaml_in_profiles_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    res = CliRunner().invoke(cli, ["profile", "from-template",
                                   "nema17-bipolar-2A", "--as", "wrist"])
    assert res.exit_code == 0, res.output
    out = tmp_path / "profiles" / "wrist.yaml"
    assert out.exists()
    assert "id: wrist" in out.read_text()


def test_from_template_unknown_returns_nonzero(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    res = CliRunner().invoke(cli, ["profile", "from-template",
                                   "nope", "--as", "wrist"])
    assert res.exit_code != 0


def test_from_template_refuses_overwrite_without_force(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["profile", "from-template",
                        "nema17-bipolar-2A", "--as", "wrist"])
    res = runner.invoke(cli, ["profile", "from-template",
                              "nema17-bipolar-2A", "--as", "wrist"])
    assert res.exit_code != 0
    assert "exists" in res.output.lower()


def test_from_template_force_overwrites(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(cli, ["profile", "from-template",
                        "nema17-bipolar-2A", "--as", "wrist"])
    res = runner.invoke(cli, ["profile", "from-template",
                              "nema17-bipolar-2A", "--as", "wrist", "--force"])
    assert res.exit_code == 0


def test_from_template_custom_out_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out_path = tmp_path / "custom" / "wrist.yaml"
    res = CliRunner().invoke(cli, ["profile", "from-template",
                                   "nema17-bipolar-2A", "--as", "wrist",
                                   "--out", str(out_path)])
    assert res.exit_code == 0, res.output
    assert out_path.exists()
