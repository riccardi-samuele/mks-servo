from unittest.mock import MagicMock, patch
import logging
import pytest
from mks_servo.motor import Motor
from mks_servo.profile import Profile, DriverSection


def _make_profile_with_path(tmp_path):
    p = Profile(id="t", driver=DriverSection(model="servo42d", slave_addr=1))
    p.path = tmp_path / "t.yaml"
    return p


def test_auto_save_off_by_default(tmp_path, mock_raw):
    p = _make_profile_with_path(tmp_path)
    with patch.object(Profile, "save") as save:
        m = Motor(p, raw=mock_raw); m.attach()
        m.work_current_ma = 2000
        save.assert_not_called()


def test_auto_save_on_writes_yaml_after_setter(tmp_path, mock_raw):
    p = _make_profile_with_path(tmp_path)
    with patch.object(Profile, "save") as save:
        m = Motor(p, raw=mock_raw, auto_save=True); m.attach()
        m.work_current_ma = 2000
        save.assert_called()


def test_auto_save_on_microsteps_and_direction_setters(tmp_path, mock_raw):
    from mks_servo.constants import Direction
    p = _make_profile_with_path(tmp_path)
    with patch.object(Profile, "save") as save:
        m = Motor(p, raw=mock_raw, auto_save=True); m.attach()
        m.microsteps = 32
        m.direction = Direction.CCW
        m.hold_current_pct = 30
        # Each setter triggered save at least once
        assert save.call_count >= 3


def test_auto_save_on_set_origin(tmp_path, mock_raw):
    p = _make_profile_with_path(tmp_path)
    with patch.object(Profile, "save") as save:
        m = Motor(p, raw=mock_raw, auto_save=True); m.attach()
        save.reset_mock()
        m.set_origin()
        save.assert_called()


def test_auto_save_does_not_save_on_write(tmp_path, mock_raw):
    p = _make_profile_with_path(tmp_path)
    with patch.object(Profile, "save") as save:
        m = Motor(p, raw=mock_raw, auto_save=True); m.attach()
        save.reset_mock()
        m.write(0, blocking=False)
        save.assert_not_called()


def test_auto_save_does_not_save_on_read(tmp_path, mock_raw):
    p = _make_profile_with_path(tmp_path)
    with patch.object(Profile, "save") as save:
        m = Motor(p, raw=mock_raw, auto_save=True); m.attach()
        save.reset_mock()
        _ = m.read()
        _ = m.position_counts
        save.assert_not_called()


def test_auto_save_no_op_for_template_profile(mock_raw, base_profile, caplog):
    # base_profile has path=None
    base_profile.path = None
    with caplog.at_level(logging.WARNING):
        m = Motor(base_profile, raw=mock_raw, auto_save=True); m.attach()
        m.work_current_ma = 2000  # would save, but path is None → warning only
    # No exception. Warning was emitted at least once.
    assert any("auto_save" in r.message.lower() or "path" in r.message.lower()
               for r in caplog.records)
