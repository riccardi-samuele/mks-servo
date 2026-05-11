"""Level-2 namespaces for the Motor class.

`motor.advanced` — driver-flash settings not needed for everyday motion.
`motor.diagnostics` — read-only health + protection-clear actions.

These are thin wrappers; each method delegates to `motor.raw.<method>` (with
a fallback to `motor.raw._txn(opcode, data, ...)` when no wrapper exists yet).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from mks_servo.constants import OpCode

if TYPE_CHECKING:
    from mks_servo.motor import Motor


class AdvancedNamespace:
    """Driver-flash-modifying configuration NOT needed for everyday motion."""

    def __init__(self, motor: "Motor"):
        self._motor = motor

    def set_baud(self, baud: int) -> None:
        """Cmd 0x8A: change the serial baud rate. Persists in driver flash.
        Caller is responsible for reconnecting at the new baud."""
        self._motor._require_attached()
        if hasattr(self._motor.raw, "set_baud"):
            self._motor.raw.set_baud(baud)
        else:
            # Translate baud to firmware code via BaudRate enum if possible.
            from mks_servo.constants import BaudRate
            try:
                code = BaudRate(int(baud)).value if isinstance(baud, int) else int(baud)
            except (ValueError, KeyError):
                code = int(baud)
            self._motor.raw._txn(
                OpCode.SET_BAUD, bytes([code & 0xFF]), expect_payload_len=1
            )
        # Update profile to reflect the new baud.
        self._motor.profile.transport.baud = int(baud)

    def set_slave_addr(self, addr: int) -> None:
        """Cmd 0x8B: change slave address. Persists in flash.
        The profile and the underlying RawDriver's addr are both updated."""
        self._motor._require_attached()
        addr = int(addr)
        if hasattr(self._motor.raw, "set_slave_addr"):
            self._motor.raw.set_slave_addr(addr)
        else:
            self._motor.raw._txn(
                OpCode.SET_SLAVE_ADDR, bytes([addr & 0xFF]), expect_payload_len=1
            )
        self._motor.profile.driver.slave_addr = addr
        # The RawDriver targets the new addr from now on (so subsequent
        # transacts use it).
        self._motor.raw.addr = addr

    def set_respond_active(self, active: bool) -> None:
        """Cmd 0x8C: enable/disable active response from the driver."""
        self._motor._require_attached()
        if hasattr(self._motor.raw, "set_respond_active"):
            self._motor.raw.set_respond_active(active)
        else:
            self._motor.raw._txn(
                OpCode.SET_RESPOND_ACTIVE,
                bytes([0x01 if active else 0x00]),
                expect_payload_len=1,
            )

    def save_speed_mode_state(self) -> None:
        """Persist the current speed-mode setting (RawDriver method)."""
        self._motor._require_attached()
        if hasattr(self._motor.raw, "save_speed_mode_state"):
            self._motor.raw.save_speed_mode_state()
        else:
            raise NotImplementedError(
                "save_speed_mode_state not exposed on RawDriver in this version"
            )


class DiagnosticsNamespace:
    """Read-only diagnostics + protection-clear actions."""

    def __init__(self, motor: "Motor"):
        self._motor = motor

    def protection_latched(self) -> bool:
        """Cmd 0x3E: True if motor stall-protection is currently latched."""
        self._motor._require_attached()
        return bool(self._motor.raw.read_protect_status())

    def release_protection(self) -> None:
        """Cmd 0x3D: clear stall-protection latch."""
        self._motor._require_attached()
        self._motor.raw.release_protection()

    def pulses_received(self) -> int:
        """Cmd 0x33: cumulative pulses received since power-on."""
        self._motor._require_attached()
        return int(self._motor.raw.read_pulses())

    def status_text(self) -> str:
        """Human-readable motor status (e.g., 'STOPPED', 'CALIBRATING')."""
        self._motor._require_attached()
        return self._motor.raw.read_motor_status().name
