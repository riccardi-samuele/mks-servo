from click.testing import CliRunner
from mks_servo.cli.__main__ import cli


def test_cli_help_shows_profile_subcommand():
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "profile" in result.output


def test_profile_help_shows_subcommands():
    result = CliRunner().invoke(cli, ["profile", "--help"])
    assert result.exit_code == 0
    for sub in ("from-driver", "from-template", "validate", "show"):
        assert sub in result.output


def test_cli_version_flag():
    result = CliRunner().invoke(cli, ["--version"])
    assert result.exit_code == 0
