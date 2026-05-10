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
    assert hasattr(mks_servo, "SharedTransport")


def test_version_string_present():
    import mks_servo
    assert hasattr(mks_servo, "__version__")
    assert mks_servo.__version__ == "0.1.0"


def test_motorbus_exported():
    import mks_servo
    assert hasattr(mks_servo, "MotorBus")
    assert hasattr(mks_servo, "BusEntry")


def test_namespaces_exported():
    import mks_servo
    assert hasattr(mks_servo, "AdvancedNamespace")
    assert hasattr(mks_servo, "DiagnosticsNamespace")
