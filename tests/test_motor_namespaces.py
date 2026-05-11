from mks_servo.namespaces import AdvancedNamespace, DiagnosticsNamespace


def test_advanced_namespace_has_methods():
    motor = object()
    ns = AdvancedNamespace(motor)
    assert ns._motor is motor
    for m in ("set_baud", "set_slave_addr", "set_respond_active",
              "save_speed_mode_state"):
        assert callable(getattr(ns, m))


def test_diagnostics_namespace_has_methods():
    motor = object()
    ns = DiagnosticsNamespace(motor)
    assert ns._motor is motor
    for m in ("protection_latched", "release_protection",
              "pulses_received", "status_text"):
        assert callable(getattr(ns, m))


def test_motor_advanced_lazy_property(base_profile, mock_raw):
    from mks_servo.motor import Motor
    m = Motor(base_profile, raw=mock_raw); m.attach()
    ns = m.advanced
    assert ns._motor is m
    # Same instance on subsequent access (lazy cache).
    assert m.advanced is ns


def test_motor_diagnostics_lazy_property(base_profile, mock_raw):
    from mks_servo.motor import Motor
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.diagnostics is m.diagnostics


def test_motor_advanced_set_slave_addr_updates_profile(base_profile, mock_raw):
    from mks_servo.motor import Motor
    base_profile.driver.slave_addr = 1
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.advanced.set_slave_addr(7)
    assert m.profile.driver.slave_addr == 7
    assert m.raw.addr == 7


def test_motor_diagnostics_protection_latched(base_profile, mock_raw):
    from mks_servo.motor import Motor
    mock_raw.read_protect_status.return_value = True
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.diagnostics.protection_latched() is True


def test_motor_diagnostics_status_text(base_profile, mock_raw):
    from mks_servo.motor import Motor
    from mks_servo.raw import MotorStatus
    mock_raw.read_motor_status.return_value = MotorStatus.STOPPED
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.diagnostics.status_text() == "STOPPED"


def test_motor_advanced_set_baud_updates_profile(base_profile, mock_raw):
    from mks_servo.motor import Motor
    m = Motor(base_profile, raw=mock_raw); m.attach()
    m.advanced.set_baud(115200)
    assert m.profile.transport.baud == 115200


def test_motor_diagnostics_pulses_received(base_profile, mock_raw):
    from mks_servo.motor import Motor
    mock_raw.read_pulses.return_value = 12345
    m = Motor(base_profile, raw=mock_raw); m.attach()
    assert m.diagnostics.pulses_received() == 12345
