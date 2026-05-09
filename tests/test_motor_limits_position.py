import logging
import pytest
from mks_servo.motor import Motor
from mks_servo.exceptions import LimitExceeded


def _profile_with_pos_limits(base_profile, mn, mx, policy):
    base_profile.limits.position.min_deg = mn
    base_profile.limits.position.max_deg = mx
    base_profile.limits.position.on_violation = policy
    return base_profile


def test_position_within_range_passes(base_profile, mock_raw):
    p = _profile_with_pos_limits(base_profile, -90, 90, "reject")
    m = Motor(p, raw=mock_raw); m.attach()
    mock_raw.move_absolute_axis.reset_mock()
    m.write(45, blocking=False)
    mock_raw.move_absolute_axis.assert_called_once()


def test_position_exceeds_max_with_reject_raises(base_profile, mock_raw):
    p = _profile_with_pos_limits(base_profile, -90, 90, "reject")
    m = Motor(p, raw=mock_raw); m.attach()
    mock_raw.move_absolute_axis.reset_mock()
    with pytest.raises(LimitExceeded) as exc:
        m.write(120, blocking=False)
    assert exc.value.kind == "position"
    assert exc.value.value == 120
    assert exc.value.limit == 90
    mock_raw.move_absolute_axis.assert_not_called()


def test_position_below_min_with_reject_raises(base_profile, mock_raw):
    p = _profile_with_pos_limits(base_profile, -90, 90, "reject")
    m = Motor(p, raw=mock_raw); m.attach()
    with pytest.raises(LimitExceeded) as exc:
        m.write(-120, blocking=False)
    assert exc.value.kind == "position"
    assert exc.value.value == -120
    assert exc.value.limit == -90


def test_position_with_clamp_clamps_to_max(base_profile, mock_raw):
    p = _profile_with_pos_limits(base_profile, -90, 90, "clamp")
    m = Motor(p, raw=mock_raw); m.attach()
    mock_raw.move_absolute_axis.reset_mock()
    m.write(120, blocking=False)
    args, kwargs = mock_raw.move_absolute_axis.call_args
    counts = kwargs.get("counts", args[0])
    # 90° → 4096 counts (no gear, no offset)
    assert counts == 4096


def test_position_with_clamp_clamps_to_min(base_profile, mock_raw):
    p = _profile_with_pos_limits(base_profile, -90, 90, "clamp")
    m = Motor(p, raw=mock_raw); m.attach()
    m.write(-120, blocking=False)
    args, kwargs = mock_raw.move_absolute_axis.call_args
    counts = kwargs.get("counts", args[0])
    # -90° → -4096
    assert counts == -4096


def test_position_with_warn_proceeds_and_logs(base_profile, mock_raw, caplog):
    p = _profile_with_pos_limits(base_profile, -90, 90, "warn")
    m = Motor(p, raw=mock_raw); m.attach()
    mock_raw.move_absolute_axis.reset_mock()
    with caplog.at_level(logging.WARNING):
        m.write(120, blocking=False)
    assert any("position" in r.message for r in caplog.records)
    mock_raw.move_absolute_axis.assert_called_once()


def test_position_with_no_limits_does_not_check(base_profile, mock_raw):
    base_profile.limits.position.min_deg = None
    base_profile.limits.position.max_deg = None
    m = Motor(base_profile, raw=mock_raw); m.attach()
    mock_raw.move_absolute_axis.reset_mock()
    m.write(10000, blocking=False)
    mock_raw.move_absolute_axis.assert_called_once()
