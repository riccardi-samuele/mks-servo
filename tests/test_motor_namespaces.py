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
