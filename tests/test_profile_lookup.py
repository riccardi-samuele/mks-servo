import textwrap
from pathlib import Path
import pytest
from mks_servo.profile import Profile
from mks_servo.exceptions import ProfileError


YAML_CONTENT = textwrap.dedent("""
    schema_version: 1
    id: wrist
    driver:
      model: servo42d
      slave_addr: 1
""").lstrip()


def test_lookup_finds_project_profile(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "profiles").mkdir()
    (tmp_path / "profiles" / "wrist.yaml").write_text(YAML_CONTENT)
    p = Profile.load("wrist")
    assert p.path == (tmp_path / "profiles" / "wrist.yaml").resolve()


def test_lookup_falls_back_to_user_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    user_dir = tmp_path / "userhome" / ".config" / "mks-servo" / "profiles"
    user_dir.mkdir(parents=True)
    (user_dir / "elbow.yaml").write_text(YAML_CONTENT.replace("wrist", "elbow"))
    monkeypatch.setenv("HOME", str(tmp_path / "userhome"))
    p = Profile.load("elbow")
    assert p.id == "elbow"
    assert p.path == (user_dir / "elbow.yaml").resolve()


def test_lookup_fails_when_not_found(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    with pytest.raises(ProfileError, match="not found"):
        Profile.load("nonexistent_motor")
