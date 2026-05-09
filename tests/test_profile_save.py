import textwrap
from pathlib import Path
import pytest
from mks_servo.profile import Profile
from mks_servo.exceptions import ProfileError


def test_save_round_trip_preserves_user_comments(tmp_path):
    src = tmp_path / "wrist.yaml"
    src.write_text(textwrap.dedent("""
        schema_version: 1
        id: wrist
        # this is a user comment about the slave addr
        driver:
          model: servo42d
          slave_addr: 1
    """).lstrip())

    p = Profile.load(str(src))
    p.config.work_current_ma = 1700
    p.save()
    text = src.read_text()
    assert "user comment about the slave addr" in text
    assert "work_current_ma: 1700" in text


def test_save_updates_updated_at(tmp_path):
    src = tmp_path / "wrist.yaml"
    src.write_text(textwrap.dedent("""
        schema_version: 1
        id: wrist
        driver:
          model: servo42d
          slave_addr: 1
    """).lstrip())
    p = Profile.load(str(src))
    p.save()
    p2 = Profile.load(str(src))
    assert p2.updated_at is not None


def test_save_template_loaded_without_path_raises(tmp_path):
    p = Profile.from_template("nema17-bipolar-2A", id="wrist")
    with pytest.raises(ProfileError, match="path"):
        p.save()


def test_save_template_with_explicit_path_works(tmp_path):
    p = Profile.from_template("nema17-bipolar-2A", id="wrist")
    target = tmp_path / "wrist.yaml"
    p.save(target)
    assert target.exists()
    p2 = Profile.load(str(target))
    assert p2.id == "wrist"
