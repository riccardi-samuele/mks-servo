from typing import Literal


class MKSError(Exception):
    pass


class CommTimeout(MKSError):
    pass


class ChecksumError(MKSError):
    pass


class ProtocolError(MKSError):
    pass


class MotorFault(MKSError):
    pass


class CalibrationFailed(MotorFault):
    pass


class ProfileError(MKSError):
    """Profile schema invalid, file corrupt, range out of bounds, or unknown schema_version."""

    def __init__(self, message: str, *, violations: list[str] | None = None):
        super().__init__(message)
        self.violations: list[str] = list(violations) if violations else []


class LimitExceeded(MKSError):
    """A command was rejected because it violated a software limit declared in a Profile.

    Attributes:
        kind: which category was violated.
        value: the offending value.
        limit: the configured limit.
    """

    def __init__(self,
                 kind: Literal["position", "speed", "current"],
                 value: float, limit: float, message: str | None = None):
        if message is None:
            message = f"{kind} limit exceeded: value={value} limit={limit}"
        super().__init__(message)
        self.kind = kind
        self.value = value
        self.limit = limit


class MotorNotAttached(MKSError):
    """A method requiring an open serial transport was called before `attach()`."""
