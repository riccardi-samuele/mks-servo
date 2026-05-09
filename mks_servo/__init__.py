"""MKS SERVO42D RS485 driver and characterization library."""
from .raw import RawDriver, MotorStatus
from .constants import WorkMode, Direction, BaudRate, OpCode
from .exceptions import (
    MKSError, CommTimeout, ChecksumError, ProtocolError,
    MotorFault, CalibrationFailed,
)

# Temporary back-compat alias; removed in Task 36.
MKSServo42D = RawDriver

__version__ = "0.1.0"

__all__ = [
    "RawDriver", "MotorStatus",
    "WorkMode", "Direction", "BaudRate", "OpCode",
    "MKSError", "CommTimeout", "ChecksumError", "ProtocolError",
    "MotorFault", "CalibrationFailed",
    "MKSServo42D",  # back-compat alias; remove in Task 36
]
