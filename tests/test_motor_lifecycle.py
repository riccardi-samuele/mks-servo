import pytest
from mks_servo.motor import Motor
from mks_servo.exceptions import MotorNotAttached


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


def test_attach_opens_internally_owned_raw_driver(monkeypatch, tmp_path):
    """Regression: Motor.from_profile + attach() must open the serial transport.
    Pre-fix bug: RawDriver was constructed but open() never called, so the
    first transact failed with 'serial not open'."""
    import textwrap
    from unittest.mock import MagicMock
    from mks_servo.motor import Motor

    fake_serial_cls = MagicMock()
    fake_serial = MagicMock()
    fake_serial.read.return_value = b"\xfb\x01\x82\x01\x7f"  # head + addr + code + data + chk
    fake_serial_cls.return_value = fake_serial
    monkeypatch.setattr("mks_servo.raw.serial.Serial", fake_serial_cls)

    p = tmp_path / "wrist.yaml"
    p.write_text(textwrap.dedent("""
        schema_version: 1
        id: wrist
        driver:
          model: servo42d
          slave_addr: 1
        transport:
          port: /dev/ttyUSB0
          baud: 38400
          timeout_s: 1.0
    """).lstrip())

    # Patch transact to simulate driver replies (bypass real frame parsing)
    monkeypatch.setattr(
        "mks_servo.raw.transact",
        lambda *a, **kw: (1, kw.get("code", a[2] if len(a) > 2 else 0), b"\x01"),
    )

    m = Motor.from_profile(str(p))
    m.attach()
    # If attach() forgot to open the transport, fake_serial_cls would not have
    # been called and the first transact would have failed.
    assert fake_serial_cls.called
    assert m._attached is True
    m.detach()
