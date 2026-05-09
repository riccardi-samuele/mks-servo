from mks_servo.constants import WorkMode, BaudRate, OpCode, Direction


def test_workmode_serial_values():
    assert WorkMode.SR_OPEN.value == 3
    assert WorkMode.SR_CLOSE.value == 4
    assert WorkMode.SR_vFOC.value == 5


def test_baud_rate_codes():
    assert BaudRate.B38400.code == 0x04
    assert BaudRate.B38400.bps == 38400
    assert BaudRate.B115200.code == 0x06
    assert BaudRate.B115200.bps == 115200


def test_direction_values():
    assert Direction.CW.value == 0
    assert Direction.CCW.value == 1


def test_opcode_lookup():
    assert OpCode.READ_ENCODER == 0x30
    assert OpCode.MOVE_SPEED == 0xF6
    assert OpCode.CALIBRATE == 0x80
