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
