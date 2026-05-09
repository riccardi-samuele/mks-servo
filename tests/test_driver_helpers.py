from mks_servo.driver import (
    degrees_to_encoder_counts,
    encoder_counts_to_degrees,
    degrees_to_pulses,
)


def test_degrees_to_encoder_counts_one_full_turn():
    assert degrees_to_encoder_counts(360) == 0x4000


def test_degrees_to_encoder_counts_quarter_turn():
    assert degrees_to_encoder_counts(90) == 0x4000 // 4


def test_encoder_counts_to_degrees_inverse():
    assert encoder_counts_to_degrees(0x4000) == 360.0
    assert encoder_counts_to_degrees(-0x4000) == -360.0


def test_degrees_to_pulses_default_microsteps_16():
    assert degrees_to_pulses(360) == 3200


def test_degrees_to_pulses_custom_microsteps():
    assert degrees_to_pulses(360, microsteps=64) == 200 * 64
