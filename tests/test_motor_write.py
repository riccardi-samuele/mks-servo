import pytest
from mks_servo.motor import Motor
from mks_servo.exceptions import MotorNotAttached


def test_write_converts_degrees_to_counts(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    m.attach()
    mock_raw.reset_mock()
    m.write(90.0, rpm=300, acc=50, blocking=False)
    args, kwargs = mock_raw.move_absolute_axis.call_args
    counts_arg = kwargs.get("counts", args[0] if args else None)
    # 90° on a 16384-count encoder, gear_ratio=1.0 → 4096 counts.
    assert counts_arg == 4096


def test_write_uses_default_rpm_when_unspecified(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    m.attach()
    m.write(0.0, blocking=False)
    args, kwargs = mock_raw.move_absolute_axis.call_args
    rpm = kwargs.get("rpm", args[1] if len(args) > 1 else None)
    assert rpm == 300


def test_write_uses_default_acc_when_unspecified(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    m.attach()
    m.write(0.0, blocking=False)
    args, kwargs = mock_raw.move_absolute_axis.call_args
    acc = kwargs.get("acc", args[2] if len(args) > 2 else None)
    assert acc == 50


def test_write_blocking_calls_wait_until_idle(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    m.attach()
    m.write(45.0, blocking=True)
    mock_raw.wait_until_idle.assert_called_once()


def test_write_non_blocking_does_not_call_wait(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    m.attach()
    m.write(45.0, blocking=False)
    mock_raw.wait_until_idle.assert_not_called()


def test_write_applies_gear_ratio(base_profile, mock_raw):
    base_profile.mechanical.gear_ratio = 2.0  # output 90° = motor 180° = 8192 counts
    m = Motor(base_profile, raw=mock_raw)
    m.attach()
    m.write(90.0, blocking=False)
    args, kwargs = mock_raw.move_absolute_axis.call_args
    counts = kwargs.get("counts", args[0])
    assert counts == 8192


def test_write_subtracts_origin_offset(base_profile, mock_raw):
    base_profile.origin.encoder_offset_counts = 1000
    m = Motor(base_profile, raw=mock_raw)
    m.attach()
    m.write(0.0, blocking=False)
    args, kwargs = mock_raw.move_absolute_axis.call_args
    counts = kwargs.get("counts", args[0])
    # 0° → 0 counts → minus origin offset of 1000 → -1000
    assert counts == -1000


def test_write_before_attach_raises(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    with pytest.raises(MotorNotAttached):
        m.write(45.0)


def test_write_passes_timeout_to_wait_until_idle(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    m.attach()
    m.write(45.0, blocking=True, timeout=10.0)
    mock_raw.wait_until_idle.assert_called_once()
    _, kwargs = mock_raw.wait_until_idle.call_args
    assert kwargs.get("timeout") == 10.0
