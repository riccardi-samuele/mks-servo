def test_top_level_exports():
    import mks_servo
    assert hasattr(mks_servo, "Motor")
    assert hasattr(mks_servo, "Profile")
    assert hasattr(mks_servo, "RawDriver")
    assert hasattr(mks_servo, "MotorStatus")
    assert hasattr(mks_servo, "MKSError")
    assert hasattr(mks_servo, "ProfileError")
    assert hasattr(mks_servo, "LimitExceeded")
    assert hasattr(mks_servo, "MotorNotAttached")
    assert hasattr(mks_servo, "WorkMode")
    assert hasattr(mks_servo, "Direction")


def test_version_string_present():
    import mks_servo
    assert hasattr(mks_servo, "__version__")
    assert mks_servo.__version__ == "0.1.0"


def test_back_compat_alias_still_works():
    """The MKSServo42D alias is still kept for benchmarks during v0.1.0."""
    from mks_servo import MKSServo42D, RawDriver
    assert MKSServo42D is RawDriver
