"""HIL test: full calibration sequence. Requires hardware. Motor must be unloaded."""
import pytest
from mks_servo import Motor

pytestmark = pytest.mark.hil


def test_full_calibration_succeeds(hil_profile):
    with Motor(hil_profile) as m:
        m.calibrate(current_ma=3000)
        assert m.profile.characterization.last_calibrated is not None
