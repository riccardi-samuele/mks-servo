import textwrap
from click.testing import CliRunner
from mks_servo.cli.__main__ import cli


VALID = textwrap.dedent("""
    schema_version: 1
    id: wrist
    driver:
      model: servo42d
      slave_addr: 1
""").lstrip()

INVALID = textwrap.dedent("""
    schema_version: 1
    id: "bad name"
    driver:
      model: servo42d
      slave_addr: 999
""").lstrip()


def test_validate_ok_returns_zero(tmp_path):
    p = tmp_path / "wrist.yaml"
    p.write_text(VALID)
    res = CliRunner().invoke(cli, ["profile", "validate", str(p)])
    assert res.exit_code == 0, res.output
    assert "OK" in res.output


def test_validate_invalid_returns_nonzero_and_lists_violations(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text(INVALID)
    res = CliRunner().invoke(cli, ["profile", "validate", str(p)])
    assert res.exit_code != 0
    full = res.output + (res.stderr if hasattr(res, 'stderr') else "")
    assert "id" in full
    assert "slave_addr" in full


def test_validate_missing_file_returns_nonzero(tmp_path):
    res = CliRunner().invoke(cli, ["profile", "validate", str(tmp_path / "nope.yaml")])
    assert res.exit_code != 0
