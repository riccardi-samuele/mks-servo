import pytest
from mks_servo.motor import Motor


def test_set_origin_firmware_calls_set_zero_point(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.set_origin()  # default: soft=False
    mock_raw.set_zero_point.assert_called_once()
    # Soft offset stays at 0 (firmware took care of it).
    assert m.profile.origin.encoder_offset_counts == 0
    assert m.profile.origin.set_in_firmware is True


def test_set_origin_soft_stores_offset_in_profile(base_profile, mock_raw):
    mock_raw.read_encoder_addition.return_value = 7777
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.set_origin(soft=True)
    assert m.profile.origin.encoder_offset_counts == 7777
    assert m.profile.origin.set_in_firmware is False
    mock_raw.set_zero_point.assert_not_called()


def test_set_origin_soft_changes_subsequent_read(base_profile, mock_raw):
    mock_raw.read_encoder_addition.return_value = 4096   # 90°
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert abs(m.read() - 90.0) < 1e-6
    m.set_origin(soft=True)                              # zero is now here
    assert abs(m.read() - 0.0) < 1e-6                    # apparent angle = 0


def test_set_origin_before_attach_raises(base_profile, mock_raw):
    from mks_servo.exceptions import MotorNotAttached
    m = Motor(base_profile, raw=mock_raw)
    with pytest.raises(MotorNotAttached):
        m.set_origin()


def test_set_origin_firmware_resets_existing_offset(base_profile, mock_raw):
    base_profile.origin.encoder_offset_counts = 999
    base_profile.origin.set_in_firmware = False
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.set_origin()
    assert m.profile.origin.encoder_offset_counts == 0
    assert m.profile.origin.set_in_firmware is True
