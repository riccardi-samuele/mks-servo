import pytest
from mks_servo.motor import Motor
from mks_servo.exceptions import CommTimeout, MotorNotAttached


def test_motor_constructor_does_not_open_transport(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    assert m.profile is base_profile
    assert m.model == "servo42d"
    # The mock_raw should not have been used yet (no method calls)
    mock_raw.set_work_mode.assert_not_called()


def test_attach_calls_into_raw_to_apply_config(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    m.attach()
    mock_raw.set_work_mode.assert_called_once_with(base_profile.config.mode)
    mock_raw.set_subdivision.assert_called_once_with(base_profile.config.microsteps)
    mock_raw.set_work_current_ma.assert_called_once_with(base_profile.config.work_current_ma)


def test_attach_retries_config_command_once_on_comm_timeout(base_profile, mock_raw, mocker):
    """HIL regression: the MKS firmware can drop the reply to a command issued
    right after a fresh connection (adapter not settled / motor still coasting).
    attach() must settle briefly and retry once rather than blow up."""
    mock_raw.set_work_current_ma.side_effect = [CommTimeout("truncated frame"), True]
    sleep = mocker.patch("mks_servo.motor._time.sleep")
    m = Motor(base_profile, raw=mock_raw)
    m.attach()  # must not raise
    assert m._attached is True
    assert mock_raw.set_work_current_ma.call_count == 2
    sleep.assert_any_call(0.3)


def test_attach_propagates_comm_timeout_if_retry_also_fails(base_profile, mock_raw, mocker):
    """One retry only — a persistently dead link still surfaces the error."""
    mock_raw.set_work_mode.side_effect = CommTimeout("link down")
    mocker.patch("mks_servo.motor._time.sleep")
    m = Motor(base_profile, raw=mock_raw)
    with pytest.raises(CommTimeout):
        m.attach()
    assert m._attached is False


def test_attach_is_idempotent(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    m.attach()
    mock_raw.reset_mock()
    m.attach()  # no-op
    mock_raw.set_work_mode.assert_not_called()


def test_methods_before_attach_raise(base_profile, mock_raw):
    # We don't have read() yet, but _require_attached can be tested indirectly
    # via a method we'll add later. For now, test that the public attach state
    # is queryable and detach() is safe before attach.
    m = Motor(base_profile, raw=mock_raw)
    assert m._attached is False
    m.detach()  # idempotent: no-op when not attached, no exceptions
    assert m._attached is False


def test_context_manager_attaches_and_detaches(base_profile, mock_raw):
    with Motor(base_profile, raw=mock_raw) as m:
        assert m._attached is True
    assert m._attached is False
    # On exit, motor must be disabled
    mock_raw.enable.assert_any_call(False)


def test_detach_disables_motor(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    m.attach()
    m.detach()
    mock_raw.enable.assert_called_with(False)


def test_detach_is_idempotent(base_profile, mock_raw):
    m = Motor(base_profile, raw=mock_raw)
    m.detach()  # no-op when not attached
    m.attach()
    m.detach()
    m.detach()  # second detach: no-op


def test_model_property_reads_from_profile(base_profile, mock_raw):
    base_profile.driver.model = "servo42d"
    m = Motor(base_profile, raw=mock_raw)
    assert m.model == "servo42d"


def test_attach_auto_enables_motor(base_profile, mock_raw):
    """HIL regression: attach() must energise the motor (Servo-style), else
    motor.write() commands are accepted by the driver but the motor stays
    inert. detach() still disables."""
    m = Motor(base_profile, raw=mock_raw)
    m.attach()
    mock_raw.enable.assert_called_with(True)
    m.detach()
    mock_raw.enable.assert_called_with(False)


def test_attach_opens_internally_owned_raw_driver(base_profile, monkeypatch):
    """HIL regression: when Motor owns the RawDriver (created from the
    profile transport), attach() must call .open() on it — RawDriver does not
    auto-open in __init__, so the first transact would otherwise fail."""
    from unittest.mock import MagicMock
    fake_raw = MagicMock()
    fake_factory = MagicMock(return_value=fake_raw)
    monkeypatch.setattr("mks_servo.motor.make_raw_driver", fake_factory)
    base_profile.transport.port = "/dev/ttyUSB0"
    m = Motor(base_profile)  # no raw= → Motor builds + owns one
    m.attach()
    assert fake_factory.called
    fake_raw.open.assert_called_once()
