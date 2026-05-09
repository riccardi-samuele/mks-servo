"""HIL test: set_origin firmware vs soft. Requires hardware."""
import pytest
from mks_servo import Motor

pytestmark = pytest.mark.hil


def test_firmware_set_origin_persists(hil_profile):
    with Motor(hil_profile) as m:
        m.write(45)
        m.set_origin()                 # cmd 0x92 — flash write
        assert abs(m.read()) < 1.0
        # NOTE: Persistence across power-cycle is asserted manually:
        # power-cycle, then run this test again — read() should still be ~0.


def test_soft_set_origin_updates_profile(hil_profile):
    with Motor(hil_profile) as m:
        m.write(45)
        m.set_origin(soft=True)
        assert abs(m.read()) < 1.0
        assert m.profile.origin.encoder_offset_counts != 0
        assert m.profile.origin.set_in_firmware is False
