from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from mks_servo.cli.__main__ import cli
from mks_servo.bus import BusEntry


def test_bus_discover_lists_drivers(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_mode = MagicMock()
    fake_mode.name = "SR_vFOC"
    fake_entries = [
        BusEntry(addr=1, model="servo42d",
                 config={"mode": fake_mode, "current_ma": 1500,
                         "subdivision": 16}),
        BusEntry(addr=3, model="servo42d",
                 config={"mode": fake_mode, "current_ma": 1000,
                         "subdivision": 8}),
    ]
    with patch("mks_servo.cli.bus_cmds.MotorBus") as fake_bus_cls:
        fake_bus = MagicMock()
        fake_bus.__enter__.return_value = fake_bus
        fake_bus.__exit__.return_value = False
        fake_bus.scan.return_value = fake_entries
        fake_bus_cls.return_value = fake_bus
        res = CliRunner().invoke(cli, [
            "bus", "discover", "--port", "/dev/ttyUSB0",
        ])
    assert res.exit_code == 0, res.output
    assert "addr=1" in res.output
    assert "addr=3" in res.output
    assert "SR_vFOC" in res.output


def test_bus_discover_no_drivers_found(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("mks_servo.cli.bus_cmds.MotorBus") as fake_bus_cls:
        fake_bus = MagicMock()
        fake_bus.__enter__.return_value = fake_bus
        fake_bus.__exit__.return_value = False
        fake_bus.scan.return_value = []
        fake_bus_cls.return_value = fake_bus
        res = CliRunner().invoke(cli, [
            "bus", "discover", "--port", "/dev/ttyUSB0",
        ])
    assert res.exit_code == 0
    assert "no drivers" in res.output.lower()


def test_bus_discover_create_profiles_flag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_entries = [BusEntry(addr=1, model="servo42d", config={})]
    with patch("mks_servo.cli.bus_cmds.MotorBus") as fake_bus_cls:
        fake_bus = MagicMock()
        fake_bus.__enter__.return_value = fake_bus
        fake_bus.__exit__.return_value = False
        fake_bus.scan.return_value = fake_entries
        fake_bus_cls.return_value = fake_bus
        res = CliRunner().invoke(cli, [
            "bus", "discover", "--port", "/dev/ttyUSB0", "--create-profiles",
        ])
    assert res.exit_code == 0
    assert fake_bus.scan.call_args.kwargs.get("create_profiles") is True


def test_bus_discover_range_parsing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    captured = {}
    with patch("mks_servo.cli.bus_cmds.MotorBus") as fake_bus_cls:
        fake_bus = MagicMock()
        fake_bus.__enter__.return_value = fake_bus
        fake_bus.__exit__.return_value = False
        def fake_scan(rng=None, **kw):
            captured["rng"] = rng
            return []
        fake_bus.scan.side_effect = fake_scan
        fake_bus_cls.return_value = fake_bus
        res = CliRunner().invoke(cli, [
            "bus", "discover", "--port", "/dev/ttyUSB0", "--range", "5-10",
        ])
    assert res.exit_code == 0
    assert list(captured["rng"]) == list(range(5, 11))


def test_bus_discover_passes_baud_and_timeout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    captured = {}
    with patch("mks_servo.cli.bus_cmds.MotorBus") as fake_bus_cls:
        def make_bus(**kwargs):
            captured["bus_init"] = kwargs
            fake_bus = MagicMock()
            fake_bus.__enter__.return_value = fake_bus
            fake_bus.__exit__.return_value = False
            fake_bus.scan.return_value = []
            return fake_bus
        fake_bus_cls.side_effect = make_bus
        res = CliRunner().invoke(cli, [
            "bus", "discover", "--port", "/dev/ttyUSB0",
            "--baud", "115200", "--timeout", "0.5",
        ])
    assert res.exit_code == 0
    assert captured["bus_init"]["baud"] == 115200
