"""MotorBus: multi-motor coordinator on a single RS485 transport."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Union, Optional

from mks_servo.transport import SharedTransport
from mks_servo.profile import Profile
from mks_servo.motor import Motor
from mks_servo.raw import RawDriver, make_raw_driver


@dataclass
class BusEntry:
    """A driver discovered on the bus by MotorBus.scan()."""
    addr: int
    model: str
    config: dict
    profile: Optional[Profile] = None


class MotorBus:
    """Multi-motor coordinator on a single RS485 transport.

    Owns a SharedTransport. Constructs Motors that share the transport.

    Usage:
        with MotorBus("/dev/ttyUSB0") as bus:
            wrist = bus.add("./profiles/wrist.yaml")
            elbow = bus.add("./profiles/elbow.yaml")
            wrist.write(45)
            elbow.write(90)
    """

    def __init__(self, port: str, baud: int = 38400, timeout: float = 3.0):
        self._transport = SharedTransport(port=port, baud=baud, timeout=timeout)
        self._motors: list[Motor] = []

    def open(self) -> None:
        self._transport.open()

    def close(self) -> None:
        # Detach all motors (best-effort) before closing the transport.
        for m in list(self._motors):
            try:
                m.detach()
            except Exception:
                pass
        self._motors.clear()
        self._transport.close()

    def __enter__(self) -> "MotorBus":
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def __iter__(self) -> Iterator[Motor]:
        return iter(self._motors)

    def __len__(self) -> int:
        return len(self._motors)

    def __contains__(self, motor: Motor) -> bool:
        return motor in self._motors

    def add(self, profile: Union[str, Path, Profile]) -> Motor:
        """Construct a Motor whose RawDriver shares this bus's transport.
        Calls Motor.attach() automatically. Returns the new Motor."""
        if isinstance(profile, Profile):
            prof = profile
        else:
            prof = Profile.load(str(profile))
        prof.validate()

        raw = make_raw_driver(prof.driver.model,
                              addr=prof.driver.slave_addr,
                              transport=self._transport)
        motor = Motor(prof, raw=raw)
        motor.attach()
        self._motors.append(motor)
        return motor

    def remove(self, motor: Motor) -> None:
        """Detach the motor and remove from the bus's tracking list."""
        if motor in self._motors:
            try:
                motor.detach()
            except Exception:
                pass
            self._motors.remove(motor)

    def scan(self, addr_range=None, *,
             create_profiles: bool = False,
             output_dir: Optional[Path] = None,
             force: bool = False,
             timeout: float = 1.0) -> list[BusEntry]:
        """Probe each address in the range; return discovered drivers.

        Args:
            addr_range: range of slave addresses to probe (default 1..16).
            create_profiles: if True, generate profile YAMLs for each entry.
            output_dir: directory for created profiles (default ./profiles).
            force: overwrite existing profile files.
            timeout: per-address probe timeout in seconds.
        """
        if addr_range is None:
            addr_range = range(1, 17)
        if output_dir is None:
            output_dir = Path.cwd() / "profiles"

        from mks_servo.exceptions import CommTimeout

        entries: list[BusEntry] = []
        for addr in addr_range:
            raw = make_raw_driver("servo42d",
                                  addr=addr, transport=self._transport, timeout=timeout)
            try:
                cfg = raw.read_all_config()
            except CommTimeout:
                continue
            except Exception:
                # Other errors: skip this address (probably a corrupt response).
                continue

            entry = BusEntry(addr=addr, model="servo42d", config=cfg)

            if create_profiles:
                output_dir.mkdir(parents=True, exist_ok=True)
                target = output_dir / f"motor_{addr}.yaml"
                if target.exists() and not force:
                    # Skip; caller can re-run with force=True to overwrite.
                    continue
                prof = Profile.from_driver(raw, id=f"motor_{addr}")
                prof.transport.port = self._transport.port
                prof.save(target)
                entry.profile = prof

            entries.append(entry)
        return entries
