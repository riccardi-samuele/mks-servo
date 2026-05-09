import textwrap
from click.testing import CliRunner
from mks_servo.cli.__main__ import cli


YAML = textwrap.dedent("""
    schema_version: 1
    id: wrist
    driver:
      model: servo42d
      slave_addr: 1
""").lstrip()


def test_show_prints_full_yaml(tmp_path):
    p = tmp_path / "wrist.yaml"
    p.write_text(YAML)
    res = CliRunner().invoke(cli, ["profile", "show", str(p)])
    assert res.exit_code == 0, res.output
    assert "schema_version: 1" in res.output
    assert "id: wrist" in res.output
    # show always emits the resolved path it loaded
    assert "wrist.yaml" in res.output


def test_show_section_filters_output(tmp_path):
    p = tmp_path / "wrist.yaml"
    p.write_text(YAML)
    res = CliRunner().invoke(cli, ["profile", "show", str(p), "--section", "driver"])
    assert res.exit_code == 0
    assert "model: servo42d" in res.output
    # other sections should not appear
    assert "transport" not in res.output


def test_show_unknown_section_returns_nonzero(tmp_path):
    p = tmp_path / "wrist.yaml"
    p.write_text(YAML)
    res = CliRunner().invoke(cli, ["profile", "show", str(p), "--section", "frob"])
    assert res.exit_code != 0


def test_show_missing_file_returns_nonzero(tmp_path):
    res = CliRunner().invoke(cli, ["profile", "show", str(tmp_path / "nope.yaml")])
    assert res.exit_code != 0
