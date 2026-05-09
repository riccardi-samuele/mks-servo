from enum import Enum, IntEnum


class WorkMode(IntEnum):
    CR_OPEN = 0
    CR_CLOSE = 1
    CR_vFOC = 2
    SR_OPEN = 3
    SR_CLOSE = 4
    SR_vFOC = 5


class Direction(IntEnum):
    CW = 0
    CCW = 1


class BaudRate(Enum):
    B9600 = (0x01, 9600)
    B19200 = (0x02, 19200)
    B25000 = (0x03, 25000)
    B38400 = (0x04, 38400)
    B57600 = (0x05, 57600)
    B115200 = (0x06, 115200)
    B256000 = (0x07, 256000)

    def __init__(self, code: int, bps: int) -> None:
        self.code = code
        self.bps = bps


class OpCode(IntEnum):
    READ_ENCODER = 0x30
    READ_ENCODER_ADDITION = 0x31
    READ_SPEED_RPM = 0x32
    READ_PULSES = 0x33
    READ_IO = 0x34
    READ_ANGLE_ERROR = 0x39
    READ_EN_PIN = 0x3A
    READ_HOMING_STATUS = 0x3B
    RELEASE_PROTECTION = 0x3D
    READ_PROTECT_STATUS = 0x3E
    RESTORE_DEFAULTS = 0x3F
    RESTART = 0x41
    READ_ALL_CONFIG = 0x47
    CALIBRATE = 0x80
    SET_WORK_MODE = 0x82
    SET_WORK_CURRENT = 0x83
    SET_SUBDIVISION = 0x84
    SET_BAUD = 0x8A
    SET_SLAVE_ADDR = 0x8B
    SET_RESPOND_ACTIVE = 0x8C
    SET_ZERO_POINT = 0x92
    MOVE_REL_AXIS = 0xF4
    MOVE_ABS_AXIS = 0xF5
    MOVE_SPEED = 0xF6
    EMERGENCY_STOP = 0xF7
    QUERY_STATUS = 0xF1
    ENABLE = 0xF3
    MOVE_REL_PULSES = 0xFD
    MOVE_ABS_PULSES = 0xFE
    SAVE_SPEED_STATE = 0xFF


HEAD_DOWN = 0xFA  # PC -> driver
HEAD_UP = 0xFB    # driver -> PC

ENCODER_COUNTS_PER_REV = 0x4000  # 16384, 14-bit
ANGLE_ERROR_PER_REV = 51200       # 51200 -> 360°
NEMA17_FULL_STEPS = 200
