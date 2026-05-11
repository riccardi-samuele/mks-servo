from unittest.mock import MagicMock
from mks_servo.profile import Profile, DriverSection
from mks_servo.constants import WorkMode, Direction


def test_snapshot_from_updates_config_section():
    prof = Profile(id="t", driver=DriverSection(model="servo42d", slave_addr=1))
    fake_motor = MagicMock()
    fake_motor.raw.read_all_config.return_value = {
        "mode": WorkMode.SR_vFOC,
        "current_ma": 1750,
        "hold_current_pct_idx": 5,
        "subdivision": 32,
        "dir_cw": False,
        "slave_addr": 1,
        "baud_code": 0x04,
    }
    prof.snapshot_from(fake_motor)
    assert prof.config.work_current_ma == 1750
    assert prof.config.microsteps == 32
    assert prof.config.direction == Direction.CCW
    assert prof.config.hold_current_pct == 60   # idx 5 → (5+1)*10 = 60
    assert prof.config.mode == WorkMode.SR_vFOC


def test_snapshot_from_does_not_touch_other_sections():
    prof = Profile(id="t", driver=DriverSection(model="servo42d", slave_addr=1))
    prof.limits.position.min_deg = -90.0
    prof.limits.position.max_deg = 90.0
    prof.mechanical.gear_ratio = 2.5
    fake_motor = MagicMock()
    fake_motor.raw.read_all_config.return_value = {
        "mode": WorkMode.SR_vFOC,
        "current_ma": 1500,
        "hold_current_pct_idx": 4,
        "subdivision": 16,
        "dir_cw": True,
        "slave_addr": 7,
        "baud_code": 0x04,
    }
    prof.snapshot_from(fake_motor)
    # Limits and mechanical unchanged
    assert prof.limits.position.min_deg == -90.0
    assert prof.limits.position.max_deg == 90.0
    assert prof.mechanical.gear_ratio == 2.5


def test_snapshot_from_updates_slave_addr():
    prof = Profile(id="t", driver=DriverSection(model="servo42d", slave_addr=1))
    fake_motor = MagicMock()
    fake_motor.raw.read_all_config.return_value = {
        "mode": WorkMode.SR_vFOC,
        "current_ma": 1500,
        "hold_current_pct_idx": 4,
        "subdivision": 16,
        "dir_cw": True,
        "slave_addr": 7,
        "baud_code": 0x04,
    }
    prof.snapshot_from(fake_motor)
    assert prof.driver.slave_addr == 7
