"""Tests for Profile.from_driver() — Task 9.

NOTE: read_all_config() (cmd 0x47) returns a dict whose shape differs from
the task spec's assumed shape. Actual keys/types:
  - "mode":               raw int (WorkMode byte value)
  - "current_ma":         int milliamps          (spec assumed "work_current_ma")
  - "hold_current_pct_idx": int index 0-8 → pct  (spec assumed "hold_current_pct")
  - "subdivision":        int microsteps         (spec assumed "microsteps")
  - "dir_cw":             bool (True=CW)         (spec assumed "direction": Direction)
  - "slave_addr":         int                    (matches)
  - "baud_code":          int code (BaudRate.code) (spec assumed "baud": int bps)
  - "raw":                bytes (full payload)

The return_value in the test mock reflects the actual shape.
"""
from unittest.mock import MagicMock
from mks_servo.profile import Profile
from mks_servo.constants import WorkMode, Direction


def test_from_driver_populates_config_from_introspection():
    raw = MagicMock()
    # Actual shape returned by RawDriver.read_all_config() (cmd 0x47):
    #   mode=5 → WorkMode.SR_vFOC, current_ma=1800, hold_current_pct_idx=4 → 50%,
    #   subdivision=32, dir_cw=True → Direction.CW, slave_addr=3, baud_code=4 → 38400
    raw.read_all_config.return_value = {
        "mode": 5,                   # WorkMode.SR_vFOC
        "current_ma": 1800,
        "hold_current_pct_idx": 4,   # index 4 → 50%  (indices 0-8 map to 10,20,...,90)
        "subdivision": 32,
        "en_active": 1,
        "dir_cw": True,              # True → Direction.CW
        "auto_screen_off": False,
        "stall_protect": False,
        "interp_enabled": True,
        "baud_code": 4,              # code 4 → 38400 bps (see BaudRate enum)
        "slave_addr": 3,
        "raw": b"\x00" * 12,
    }
    p = Profile.from_driver(raw, id="wrist")
    assert p.id == "wrist"
    assert p.config.mode == WorkMode.SR_vFOC
    assert p.config.work_current_ma == 1800
    assert p.config.microsteps == 32
    assert p.config.hold_current_pct == 50
    assert p.config.direction == Direction.CW
    assert p.driver.slave_addr == 3
    assert p.transport.baud == 38400
    assert p.path is None
    assert p.created_at is not None
    # Limits / mechanical / characterization NOT populated (not knowable from driver).
    assert p.limits.position.min_deg is None
    assert p.mechanical.gear_ratio == 1.0
    assert p.characterization.last_calibrated is None
    p.validate()


def test_from_driver_direction_ccw():
    """dir_cw=False maps to Direction.CCW."""
    raw = MagicMock()
    raw.read_all_config.return_value = {
        "mode": 5,
        "current_ma": 1500,
        "hold_current_pct_idx": 4,
        "subdivision": 16,
        "en_active": 1,
        "dir_cw": False,             # CCW
        "auto_screen_off": False,
        "stall_protect": False,
        "interp_enabled": True,
        "baud_code": 4,
        "slave_addr": 1,
        "raw": b"\x00" * 12,
    }
    p = Profile.from_driver(raw, id="joint1")
    assert p.config.direction == Direction.CCW


def test_from_driver_baud_115200():
    """baud_code=6 maps to 115200 bps."""
    raw = MagicMock()
    raw.read_all_config.return_value = {
        "mode": 3,                   # WorkMode.SR_OPEN
        "current_ma": 1000,
        "hold_current_pct_idx": 2,   # index 2 → 30%
        "subdivision": 8,
        "en_active": 1,
        "dir_cw": True,
        "auto_screen_off": False,
        "stall_protect": False,
        "interp_enabled": False,
        "baud_code": 6,              # code 6 → 115200 bps
        "slave_addr": 2,
        "raw": b"\x00" * 12,
    }
    p = Profile.from_driver(raw, id="joint2")
    assert p.transport.baud == 115200
    assert p.config.hold_current_pct == 30
    assert p.config.mode == WorkMode.SR_OPEN


def test_from_driver_uses_read_all_config_once():
    """from_driver() must call read_all_config exactly once, nothing else on raw."""
    raw = MagicMock()
    raw.read_all_config.return_value = {
        "mode": 5,
        "current_ma": 1500,
        "hold_current_pct_idx": 4,
        "subdivision": 16,
        "en_active": 1,
        "dir_cw": True,
        "auto_screen_off": False,
        "stall_protect": False,
        "interp_enabled": True,
        "baud_code": 4,
        "slave_addr": 1,
        "raw": b"\x00" * 12,
    }
    Profile.from_driver(raw, id="motor1")
    raw.read_all_config.assert_called_once_with()
    # No mutation calls (set_*, move_*) must have been made.
    # mock.method_calls is a list of call objects; each has a .name attribute
    # (or can be unpacked as (name, args, kwargs) — use positional index 0).
    for call in raw.method_calls:
        name = call[0]  # call[0] is the method name string
        assert name == "read_all_config", (
            f"from_driver must be read-only on the driver, but called: {name}"
        )
