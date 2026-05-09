"""MKS SERVO42D RS485 driver and characterization library."""
from .driver import MKSServo42D, MotorStatus
from .constants import WorkMode, BaudRate, Direction, OpCode
from .exceptions import (
    MKSError, CommTimeout, ChecksumError, ProtocolError, MotorFault, CalibrationFailed,
)

__version__ = "0.1.0"

__all__ = [
    "MKSServo42D", "MotorStatus",
    "WorkMode", "BaudRate", "Direction", "OpCode",
    "MKSError", "CommTimeout", "ChecksumError", "ProtocolError", "MotorFault", "CalibrationFailed",
]
