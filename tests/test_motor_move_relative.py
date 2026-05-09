import pytest
from mks_servo.motor import Motor
from mks_servo.exceptions import LimitExceeded, MotorNotAttached


def test_move_relative_adds_to_current_position(base_profile, mock_raw):
    mock_raw.read_encoder_addition.return_value = 4096   # currently at 90°
    m = Motor(base_profile, raw=mock_raw); m.attach()
    mock_raw.move_absolute_axis.reset_mock()
    m.move_relative(45.0, blocking=False)
    args, kwargs = mock_raw.move_absolute_axis.call_args
    counts = kwargs.get("counts", args[0])
    # 90 + 45 = 135° → 6144 counts (no gear, no offset)
    assert counts == 6144


def test_move_relative_negative_delta(base_profile, mock_raw):
    mock_raw.read_encoder_addition.return_value = 4096   # 90°
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.move_relative(-30.0, blocking=False)
    args, kwargs = mock_raw.move_absolute_axis.call_args
    counts = kwargs.get("counts", args[0])
    # 90 - 30 = 60° → 2730 counts (rounded)
    assert counts == round(60.0 / 360.0 * 0x4000)


def test_move_relative_applies_position_limits(base_profile, mock_raw):
    base_profile.limits.position.min_deg = -90
    base_profile.limits.position.max_deg = 90
    base_profile.limits.position.on_violation = "reject"
    mock_raw.read_encoder_addition.return_value = 4096   # 90°
    m = Motor(base_profile, raw=mock_raw); m.attach()
    with pytest.raises(LimitExceeded):
        m.move_relative(10, blocking=False)  # would land at 100°


def test_move_relative_passes_rpm_and_acc(base_profile, mock_raw):
    mock_raw.read_encoder_addition.return_value = 0
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.move_relative(10.0, rpm=600, acc=100, blocking=False)
    args, kwargs = mock_raw.move_absolute_axis.call_args
    rpm = kwargs.get("rpm", args[1] if len(args) > 1 else None)
    acc = kwargs.get("acc", args[2] if len(args) > 2 else None)
    assert rpm == 600
    assert acc == 100


def test_enable_with_default_calls_raw_with_true(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    mock_raw.enable.reset_mock()
    m.enable()
    mock_raw.enable.assert_called_with(True)


def test_enable_false_disables(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    mock_raw.enable.reset_mock()
    m.enable(False)
    mock_raw.enable.assert_called_with(False)


def test_disable_calls_raw_enable_false(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    mock_raw.enable.reset_mock()
    m.disable()
    mock_raw.enable.assert_called_with(False)


def test_wait_until_idle_passes_timeout(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.wait_until_idle(timeout=5.0)
    mock_raw.wait_until_idle.assert_called_with(timeout=5.0)


def test_wait_until_idle_default_no_timeout(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.wait_until_idle()
    mock_raw.wait_until_idle.assert_called_with(timeout=None)


def test_methods_before_attach_raise(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    with pytest.raises(MotorNotAttached):
        m.move_relative(10)
    with pytest.raises(MotorNotAttached):
        m.enable(True)
    with pytest.raises(MotorNotAttached):
        m.disable()
    with pytest.raises(MotorNotAttached):
        m.wait_until_idle()
