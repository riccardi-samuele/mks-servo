import pytest
from mks_servo.profile import Profile
from mks_servo.exceptions import ProfileError


def test_from_template_returns_valid_profile_with_overridden_id():
    p = Profile.from_template("nema17-bipolar-2A", id="wrist")
    assert p.id == "wrist"
    assert p.driver.model == "servo42d"
    assert p.path is None  # template-loaded → no auto-save target
    assert p.created_at is not None
    p.validate()  # must be valid


def test_from_template_unknown_template_raises():
    with pytest.raises(ProfileError, match="template"):
        Profile.from_template("does-not-exist", id="x")
