"""mks-servo — Python library for MKS SERVO RS485 stepper drivers."""

from mks_servo.constants import (
    WorkMode, Direction, BaudRate, OpCode,
)
from mks_servo.exceptions import (
    MKSError, CommTimeout, ChecksumError, ProtocolError,
    MotorFault, CalibrationFailed,
    ProfileError, LimitExceeded, MotorNotAttached,
)
from mks_servo.raw import RawDriver, MotorStatus
from mks_servo.profile import Profile
from mks_servo.motor import Motor

# Temporary back-compat alias; removed in Task 36.
MKSServo42D = RawDriver

__version__ = "0.1.0"

__all__ = [
    "Motor", "Profile", "RawDriver", "MotorStatus",
    "WorkMode", "Direction", "BaudRate", "OpCode",
    "MKSError", "CommTimeout", "ChecksumError", "ProtocolError",
    "MotorFault", "CalibrationFailed",
    "ProfileError", "LimitExceeded", "MotorNotAttached",
    "MKSServo42D",  # back-compat alias; remove in Task 36
    "__version__",
]
