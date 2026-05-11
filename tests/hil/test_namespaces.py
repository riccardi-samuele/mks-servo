"""HIL: Level-2 namespaces (motor.diagnostics, motor.advanced) against real
hardware. Requires the rig.

Only safe operations are exercised. The flash-modifying `advanced.set_baud()`
and `advanced.set_slave_addr()` are intentionally NOT HIL-tested here: they
would break the live connection (and any failure mid-write could leave the
driver on an unknown baud/address). They're covered by the mocked unit tests."""
import pytest

from mks_servo import Motor
from mks_servo.raw import MotorStatus

pytestmark = pytest.mark.hil


def test_diagnostics_reads(hil_profile):
    with Motor(hil_profile) as m:
        d = m.diagnostics

        # status_text: a valid MotorStatus name. At rest it should be STOPPED.
        st = d.status_text()
        assert st in MotorStatus.__members__
        assert st == "STOPPED"

        # protection_latched: a bool. After a clean attach it should be False.
        latched = d.protection_latched()
        assert isinstance(latched, bool)
        assert latched is False

        # pulses_received: an int (cumulative since power-on; sign/magnitude
        # depend on history, so we only check the type).
        pulses = d.pulses_received()
        assert isinstance(pulses, int)


def test_diagnostics_release_protection_is_safe_when_not_latched(hil_profile):
    """release_protection() must not raise even when nothing is latched."""
    with Motor(hil_profile) as m:
        m.diagnostics.release_protection()
        assert m.diagnostics.protection_latched() is False


def test_diagnostics_status_text_tracks_motion(hil_profile):
    """While a non-blocking move is in flight, status_text() should report a
    moving state; once idle it returns to STOPPED."""
    with Motor(hil_profile) as m:
        m.set_origin()
        m.write(120, rpm=120, blocking=False)
        seen_moving = False
        # Poll briefly for a moving state.
        import time
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            st = m.diagnostics.status_text()
            if st != "STOPPED":
                seen_moving = True
                break
            time.sleep(0.02)
        m.wait_until_idle()
        assert seen_moving, "status_text() never left STOPPED during a move"
        assert m.diagnostics.status_text() == "STOPPED"
        m.write(0)


def test_advanced_set_respond_active_does_not_raise(hil_profile):
    """set_respond_active(True) re-asserts the driver's default (active
    responses). Harmless to issue; we only check it round-trips without error
    and the driver still answers afterwards."""
    with Motor(hil_profile) as m:
        m.advanced.set_respond_active(True)
        # Driver must still respond after the call.
        assert m.diagnostics.status_text() == "STOPPED"
