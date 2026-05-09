from unittest.mock import patch, MagicMock
from mks_servo.bus import MotorBus, BusEntry
from mks_servo.exceptions import CommTimeout
from mks_servo.constants import WorkMode


def _config_dict(addr=1):
    return {
        "mode": WorkMode.SR_vFOC, "current_ma": 1500,
        "hold_current_pct_idx": 4, "subdivision": 16,
        "dir_cw": True, "slave_addr": addr, "baud_code": 0x04,
    }


def test_scan_returns_entries_for_responsive_addrs():
    """Patch RawDriver inside bus.scan so each address returns config or timeouts."""
    with patch("mks_servo.transport.serial.Serial"):
        with MotorBus("/dev/foo") as bus:
            with patch("mks_servo.bus.RawDriver") as fake_raw_cls:
                def make_raw(addr, transport, timeout=None):
                    inst = MagicMock()
                    inst.timeout = timeout
                    if addr in (1, 3):
                        inst.read_all_config.return_value = _config_dict(addr=addr)
                    else:
                        inst.read_all_config.side_effect = CommTimeout("no response")
                    return inst
                fake_raw_cls.side_effect = lambda addr, transport, timeout=None: \
                    make_raw(addr, transport, timeout=timeout)

                entries = bus.scan(range(1, 4))
                addrs = [e.addr for e in entries]
                assert 1 in addrs
                assert 3 in addrs
                assert 2 not in addrs


def test_scan_default_range_is_1_to_16():
    with patch("mks_servo.transport.serial.Serial"):
        with MotorBus("/dev/foo") as bus:
            calls = []
            with patch("mks_servo.bus.RawDriver") as fake_raw_cls:
                def make_raw(addr, transport, timeout=None):
                    calls.append(addr)
                    inst = MagicMock()
                    inst.read_all_config.side_effect = CommTimeout("no")
                    return inst
                fake_raw_cls.side_effect = lambda addr, transport, timeout=None: \
                    make_raw(addr, transport, timeout=timeout)
                bus.scan()
            assert calls == list(range(1, 17))


def test_scan_create_profiles_writes_yaml(tmp_path):
    with patch("mks_servo.transport.serial.Serial"):
        with MotorBus("/dev/foo") as bus:
            with patch("mks_servo.bus.RawDriver") as fake_raw_cls:
                inst = MagicMock()
                inst.read_all_config.return_value = _config_dict(addr=1)
                fake_raw_cls.return_value = inst
                entries = bus.scan(range(1, 2),
                                   create_profiles=True, output_dir=tmp_path)
            assert (tmp_path / "motor_1.yaml").exists()
            assert entries[0].profile is not None


def test_scan_create_profiles_skips_existing_without_force(tmp_path):
    (tmp_path / "motor_1.yaml").write_text("# existing\n")
    with patch("mks_servo.transport.serial.Serial"):
        with MotorBus("/dev/foo") as bus:
            with patch("mks_servo.bus.RawDriver") as fake_raw_cls:
                inst = MagicMock()
                inst.read_all_config.return_value = _config_dict(addr=1)
                fake_raw_cls.return_value = inst
                entries = bus.scan(range(1, 2),
                                   create_profiles=True, output_dir=tmp_path)
            # Existing file preserved
            assert (tmp_path / "motor_1.yaml").read_text() == "# existing\n"
            # Entry should not be in the list (we skipped it) — OR it IS in the
            # list with profile=None. Either is acceptable; assert the list is
            # consistent with "no overwrite happened".
            # Decision: if the file existed and we didn't force, the entry is
            # NOT added (matches the implementation in the plan).
            assert len(entries) == 0


def test_scan_create_profiles_force_overwrites(tmp_path):
    (tmp_path / "motor_1.yaml").write_text("# existing\n")
    with patch("mks_servo.transport.serial.Serial"):
        with MotorBus("/dev/foo") as bus:
            with patch("mks_servo.bus.RawDriver") as fake_raw_cls:
                inst = MagicMock()
                inst.read_all_config.return_value = _config_dict(addr=1)
                fake_raw_cls.return_value = inst
                entries = bus.scan(range(1, 2),
                                   create_profiles=True, output_dir=tmp_path,
                                   force=True)
            text = (tmp_path / "motor_1.yaml").read_text()
            assert text != "# existing\n"  # overwritten
            assert len(entries) == 1


def test_scan_passes_timeout_to_raw():
    with patch("mks_servo.transport.serial.Serial"):
        with MotorBus("/dev/foo") as bus:
            captured_timeouts = []
            with patch("mks_servo.bus.RawDriver") as fake_raw_cls:
                def make_raw(addr, transport, timeout=None):
                    captured_timeouts.append(timeout)
                    inst = MagicMock()
                    inst.read_all_config.side_effect = CommTimeout("no")
                    return inst
                fake_raw_cls.side_effect = lambda addr, transport, timeout=None: \
                    make_raw(addr, transport, timeout=timeout)
                bus.scan(range(1, 3), timeout=0.5)
            assert all(t == 0.5 for t in captured_timeouts)
