import logging
import pytest
from mks_servo.motor import Motor
from mks_servo.exceptions import LimitExceeded


def _set_speed_limit(p, max_rpm, policy):
    p.limits.speed.max_rpm_safe = max_rpm
    p.limits.speed.on_violation = policy
    return p


def test_speed_within_range_passes(base_profile, mock_raw):
    p = _set_speed_limit(base_profile, 1500, "clamp")
    m = Motor(p, raw=mock_raw); m.attach()
    mock_raw.move_absolute_axis.reset_mock()
    m.write(0, rpm=1000, blocking=False)
    args, kwargs = mock_raw.move_absolute_axis.call_args
    rpm = kwargs.get("rpm", args[1])
    assert rpm == 1000


def test_speed_exceeds_with_reject_raises(base_profile, mock_raw):
    p = _set_speed_limit(base_profile, 1300, "reject")
    m = Motor(p, raw=mock_raw); m.attach()
    mock_raw.move_absolute_axis.reset_mock()
    with pytest.raises(LimitExceeded) as exc:
        m.write(0, rpm=2000, blocking=False)
    assert exc.value.kind == "speed"
    assert exc.value.value == 2000
    assert exc.value.limit == 1300
    mock_raw.move_absolute_axis.assert_not_called()


def test_speed_with_clamp_clamps(base_profile, mock_raw):
    p = _set_speed_limit(base_profile, 1300, "clamp")
    m = Motor(p, raw=mock_raw); m.attach()
    mock_raw.move_absolute_axis.reset_mock()
    m.write(0, rpm=2000, blocking=False)
    args, kwargs = mock_raw.move_absolute_axis.call_args
    rpm = kwargs.get("rpm", args[1])
    assert rpm == 1300


def test_speed_with_warn_proceeds_and_logs(base_profile, mock_raw, caplog):
    p = _set_speed_limit(base_profile, 1300, "warn")
    m = Motor(p, raw=mock_raw); m.attach()
    mock_raw.move_absolute_axis.reset_mock()
    with caplog.at_level(logging.WARNING):
        m.write(0, rpm=2000, blocking=False)
    assert any("speed" in r.message for r in caplog.records)
    args, kwargs = mock_raw.move_absolute_axis.call_args
    rpm = kwargs.get("rpm", args[1])
    assert rpm == 2000


def test_speed_no_limit_does_not_check(base_profile, mock_raw):
    base_profile.limits.speed.max_rpm_safe = None
    m = Motor(base_profile, raw=mock_raw); m.attach()
    mock_raw.move_absolute_axis.reset_mock()
    m.write(0, rpm=99999, blocking=False)
    mock_raw.move_absolute_axis.assert_called_once()
    args, kwargs = mock_raw.move_absolute_axis.call_args
    rpm = kwargs.get("rpm", args[1])
    assert rpm == 99999
