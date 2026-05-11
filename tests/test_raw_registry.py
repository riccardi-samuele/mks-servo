import pytest
from mks_servo.raw import DRIVER_REGISTRY, RawDriver, make_raw_driver
from mks_servo.exceptions import ProfileError


def test_registry_has_servo42d():
    assert "servo42d" in DRIVER_REGISTRY
    assert DRIVER_REGISTRY["servo42d"] is RawDriver


def test_make_raw_driver_servo42d_returns_rawdriver_instance():
    d = make_raw_driver("servo42d", addr=1)
    assert isinstance(d, RawDriver)
    assert d.addr == 1


def test_make_raw_driver_passes_kwargs():
    d = make_raw_driver("servo42d", port="/dev/foo", baud=115200,
                        addr=5, timeout=2.0)
    assert d.port == "/dev/foo"
    assert d.baud == 115200
    assert d.addr == 5
    assert d.timeout == 2.0


def test_make_raw_driver_unknown_raises():
    with pytest.raises(ProfileError, match="unknown driver model"):
        make_raw_driver("smoothieboard", addr=1)


def test_registry_is_extensible():
    """A future driver class can be registered without modifying mks_servo."""
    class FakeDriver:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
    DRIVER_REGISTRY["fake-test-driver"] = FakeDriver
    try:
        d = make_raw_driver("fake-test-driver", port="/dev/x", addr=2)
        assert isinstance(d, FakeDriver)
        assert d.kwargs["port"] == "/dev/x"
    finally:
        del DRIVER_REGISTRY["fake-test-driver"]
