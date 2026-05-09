from mks_servo.profile import (
    Profile, DriverSection, TransportSection, ConfigSection,
    LimitsSection, PositionLimit, SpeedLimit, CurrentLimit,
    OriginSection, MechanicalSection, CharacterizationSection,
)
from mks_servo.constants import WorkMode, Direction


def test_profile_default_construction():
    p = Profile(id="wrist", driver=DriverSection(model="servo42d", slave_addr=1))
    assert p.id == "wrist"
    assert p.schema_version == 1
    assert p.driver.model == "servo42d"
    assert p.driver.slave_addr == 1
    assert p.config.mode == WorkMode.SR_vFOC
    assert p.config.microsteps == 16
    assert p.limits.position.min_deg is None
    assert p.limits.position.max_deg is None
    assert p.limits.position.on_violation == "reject"
    assert p.limits.speed.on_violation == "clamp"
    assert p.limits.current.max_ma == 3000
    assert p.origin.set_in_firmware is True
    assert p.origin.encoder_offset_counts == 0
    assert p.mechanical.gear_ratio == 1.0
    assert p.mechanical.full_steps_per_rev == 200
    assert p.characterization.last_calibrated is None


def test_profile_path_attribute_defaults_to_none():
    p = Profile(id="x", driver=DriverSection(model="servo42d", slave_addr=1))
    assert p.path is None
