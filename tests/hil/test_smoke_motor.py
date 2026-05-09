"""HIL smoke test: attach, write some angles, read back. Requires hardware."""
import pytest
from mks_servo import Motor

pytestmark = pytest.mark.hil


def test_smoke_attach_write_read(hil_profile):
    with Motor(hil_profile) as m:
        m.set_origin()
        m.write(0)
        assert abs(m.read()) < 1.0
        m.write(45, rpm=300)
        assert abs(m.read() - 45.0) < 1.0
        m.write(0)
        assert abs(m.read()) < 1.0
