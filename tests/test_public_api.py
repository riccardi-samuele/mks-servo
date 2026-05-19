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
    assert mks_servo.__version__ == "1.0.0"


def test_version_matches_pyproject():
    """Guard against the __init__/pyproject drift that bit us pre-1.0."""
    import sys
    import mks_servo
    from pathlib import Path

    if sys.version_info >= (3, 11):
        import tomllib  # type: ignore[import-not-found]
    else:
        import tomli as tomllib  # type: ignore[import-not-found]

    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    assert mks_servo.__version__ == data["project"]["version"]


def test_motorbus_exported():
    import mks_servo
    assert hasattr(mks_servo, "MotorBus")
    assert hasattr(mks_servo, "BusEntry")


def test_namespaces_exported():
    import mks_servo
    assert hasattr(mks_servo, "AdvancedNamespace")
    assert hasattr(mks_servo, "DiagnosticsNamespace")


def test_characterize_exported():
    import mks_servo
    assert hasattr(mks_servo, "CharacterizationSuite")
    assert hasattr(mks_servo, "SuiteResult")
    assert hasattr(mks_servo, "P1Result")
    assert hasattr(mks_servo, "P3Result")
    assert hasattr(mks_servo, "P5Result")
    assert hasattr(mks_servo, "S2Result")
