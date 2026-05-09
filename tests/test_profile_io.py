import textwrap
from pathlib import Path
import pytest
from mks_servo.profile import Profile
from mks_servo.exceptions import ProfileError


def write_profile(tmp_path: Path, content: str, name: str = "wrist.yaml") -> Path:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content).lstrip())
    return p


def test_load_minimal_profile_from_path(tmp_path):
    p = write_profile(tmp_path, """
        schema_version: 1
        id: wrist
        driver:
          model: servo42d
          slave_addr: 2
    """)
    prof = Profile.load(str(p))
    assert prof.id == "wrist"
    assert prof.driver.slave_addr == 2
    assert prof.path == p


def test_load_unknown_schema_version_raises(tmp_path):
    p = write_profile(tmp_path, """
        schema_version: 99
        id: wrist
        driver:
          model: servo42d
          slave_addr: 1
    """)
    with pytest.raises(ProfileError, match="schema_version"):
        Profile.load(str(p))
