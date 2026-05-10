"""mks-servo — Python library for MKS SERVO RS485 stepper drivers."""

from mks_servo.constants import (
    WorkMode, Direction, BaudRate, OpCode,
)
from mks_servo.exceptions import (
    MKSError, CommTimeout, ChecksumError, ProtocolError,
    MotorFault, CalibrationFailed,
    ProfileError, LimitExceeded, MotorNotAttached,
)
from mks_servo.raw import RawDriver, MotorStatus, make_raw_driver, DRIVER_REGISTRY
from mks_servo.transport import SharedTransport
from mks_servo.profile import Profile
from mks_servo.motor import Motor
from mks_servo.bus import MotorBus, BusEntry
from mks_servo.namespaces import AdvancedNamespace, DiagnosticsNamespace
from mks_servo.characterize import (
    CharacterizationSuite, SuiteResult, P1Result, P3Result, P5Result, S2Result,
)

__version__ = "0.1.0"

__all__ = [
    "Motor", "Profile", "MotorBus", "BusEntry",
    "RawDriver", "MotorStatus", "make_raw_driver", "DRIVER_REGISTRY", "SharedTransport",
    "WorkMode", "Direction", "BaudRate", "OpCode",
    "MKSError", "CommTimeout", "ChecksumError", "ProtocolError",
    "MotorFault", "CalibrationFailed",
    "ProfileError", "LimitExceeded", "MotorNotAttached",
    "AdvancedNamespace", "DiagnosticsNamespace",
    "CharacterizationSuite", "SuiteResult",
    "P1Result", "P3Result", "P5Result", "S2Result",
    "__version__",
]
