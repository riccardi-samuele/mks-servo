# Stepper Motor Test (MKS SERVO42D RS485) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable Python library `mks_servo` and a benchmark suite to characterize a NEMA17 + MKS SERVO42D RS485 driver across precision, speed, and configuration persistence.

**Architecture:**
Three-layer Python package — `protocol.py` (raw frame FA/FB encode/decode), `driver.py` (high-level `MKSServo42D` class), supporting modules (`constants.py`, `exceptions.py`). On top, four standalone benchmark scripts in `benchmarks/` that import the library, drive the motor, log CSV + comm traces, and emit matplotlib plots and a markdown summary per run. Pure-Python unit tests (mocked serial) cover protocol + driver; benchmarks are hardware-in-the-loop (HIL).

**Tech Stack:** Python 3.10+, pyserial, pytest, pytest-mock, numpy, matplotlib, tomli (for `config.toml` on Python <3.11) or stdlib `tomllib` (Python 3.11+).

---

## Reference: hex test vectors from the manual (V1.0.6)

These are real bytes from the manual; use them as known-good test fixtures.

| Frame | Meaning | Notes |
|---|---|---|
| `FA 01 80 00 7B` | Calibrate, addr=01 | CRC = (0xFA+0x01+0x80+0x00) & 0xFF = 0x7B |
| `FA 01 30 2B` | Read encoder request, addr=01 | CRC = (0xFA+0x01+0x30) & 0xFF = 0x2B |
| `FB 01 30 FF FF FF FF 22 69 B3` | Encoder response: carry=0xFFFFFFFF (=-1), value=0x2269 (8809) | int32 BE + uint16 BE |
| `FA 01 F6 01 40 02 34` | Speed mode: dir=CW, speed=320 RPM, acc=2 | Manual §7.4 |
| `FA 01 FD 01 40 02 00 00 00 FA 00 35` | Position mode 1: dir=CW, speed=320 RPM, acc=2, 250 pulses | Manual §6.6 |

**Endianness:** all multi-byte values are **big-endian** (confirmed by manual §7.3 example).

---

## File structure

```
stepper_motor_test/
├── pyproject.toml
├── .gitignore
├── README.md
├── config.toml
├── pytest.ini
├── docs/
│   └── superpowers/
│       ├── specs/2026-05-09-stepper-motor-test-design.md   (already exists)
│       └── plans/2026-05-09-stepper-motor-test.md          (this file)
├── mks_servo/
│   ├── __init__.py
│   ├── exceptions.py
│   ├── constants.py
│   ├── protocol.py
│   └── driver.py
├── tests/
│   ├── __init__.py
│   ├── test_protocol.py
│   ├── test_driver_read.py
│   ├── test_driver_config.py
│   ├── test_driver_motion.py
│   └── test_driver_helpers.py
├── benchmarks/
│   ├── _common.py
│   ├── 01_smoke.py
│   ├── 02_precision.py
│   ├── 03_speed.py
│   └── 04_persistence.py
└── results/                  (gitignored)
```

---

## Task 1: Project bootstrap

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `pytest.ini`
- Create: `config.toml`
- Create: `mks_servo/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "mks-servo-test"
version = "0.1.0"
description = "Characterization tests for MKS SERVO42D RS485 + NEMA17"
requires-python = ">=3.10"
dependencies = [
    "pyserial>=3.5",
    "numpy>=1.24",
    "matplotlib>=3.7",
    "tomli>=2.0;python_version<'3.11'",
]

[project.optional-dependencies]
dev = ["pytest>=7.4", "pytest-mock>=3.11"]

[tool.pytest.ini_options]
markers = [
    "hil: requires real hardware (skipped by default)",
]
testpaths = ["tests"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["mks_servo*"]
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.pyc
.venv/
venv/
results/
*.egg-info/
.pytest_cache/
build/
dist/
```

- [ ] **Step 3: Create pytest.ini**

```ini
[pytest]
addopts = -v --strict-markers -m "not hil"
markers =
    hil: requires real hardware (skipped by default; run with -m hil)
```

- [ ] **Step 4: Create config.toml**

```toml
[serial]
port = "/dev/ttyUSB0"
baud = 38400
slave_addr = 1
timeout = 0.5

[setup]
voltage_v = 12
nema17_full_steps = 200
default_microsteps = 16
```

- [ ] **Step 5: Create empty package + tests modules**

Create `mks_servo/__init__.py`:
```python
"""MKS SERVO42D RS485 driver and characterization library."""
__version__ = "0.1.0"
```

Create `tests/__init__.py` as an empty file (zero bytes).

- [ ] **Step 6: Set up venv and install**

Run:
```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

Expected: clean install, `pytest --version` returns ≥ 7.4.

- [ ] **Step 7: Verify pytest runs (no tests yet, but config valid)**

Run: `pytest`
Expected: `no tests ran in <time>` — the run succeeds with zero collected tests.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml .gitignore pytest.ini config.toml mks_servo/__init__.py tests/__init__.py
git commit -m "chore: scaffold project (pyproject, pytest, package layout)"
```

---

## Task 2: Exceptions module

**Files:**
- Create: `mks_servo/exceptions.py`
- Create: `tests/test_exceptions.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_exceptions.py`:
```python
import pytest
from mks_servo.exceptions import (
    MKSError,
    CommTimeout,
    ChecksumError,
    ProtocolError,
    MotorFault,
    CalibrationFailed,
)


def test_all_inherit_from_mkserror():
    for cls in (CommTimeout, ChecksumError, ProtocolError, MotorFault, CalibrationFailed):
        assert issubclass(cls, MKSError)


def test_mkserror_inherits_from_exception():
    assert issubclass(MKSError, Exception)


def test_can_raise_and_catch():
    with pytest.raises(MKSError):
        raise CommTimeout("no response")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_exceptions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'mks_servo.exceptions'`.

- [ ] **Step 3: Implement exceptions module**

Create `mks_servo/exceptions.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_exceptions.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/exceptions.py tests/test_exceptions.py
git commit -m "feat(mks_servo): add exceptions module"
```

---

## Task 3: Constants module

**Files:**
- Create: `mks_servo/constants.py`
- Create: `tests/test_constants.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_constants.py`:
```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_constants.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement constants module**

Create `mks_servo/constants.py`:
```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_constants.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/constants.py tests/test_constants.py
git commit -m "feat(mks_servo): add constants (WorkMode, OpCode, BaudRate, Direction)"
```

---

## Task 4: Protocol — checksum8

**Files:**
- Create: `mks_servo/protocol.py`
- Create: `tests/test_protocol.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_protocol.py`:
```python
import pytest
from mks_servo.protocol import checksum8


def test_checksum_manual_example_calibrate():
    """Manual §4: 'FA 01 80 00 CRC' -> CRC = 0x7B."""
    assert checksum8(bytes.fromhex("FA 01 80 00")) == 0x7B


def test_checksum_manual_example_read_encoder():
    """Manual §7.3: 'FA 01 30 2B' -> CRC = 0x2B."""
    assert checksum8(bytes.fromhex("FA 01 30")) == 0x2B


def test_checksum_empty():
    assert checksum8(b"") == 0


def test_checksum_overflow_wraps_to_byte():
    # 0xFF + 0xFF = 0x1FE; & 0xFF = 0xFE
    assert checksum8(bytes([0xFF, 0xFF])) == 0xFE
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_protocol.py -v`
Expected: FAIL with import error.

- [ ] **Step 3: Implement checksum8**

Create `mks_servo/protocol.py`:
```python
def checksum8(buf: bytes) -> int:
    """8-bit modular sum (manual §4)."""
    return sum(buf) & 0xFF
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_protocol.py::test_checksum_manual_example_calibrate -v`
Expected: PASS.

Run: `pytest tests/test_protocol.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/protocol.py tests/test_protocol.py
git commit -m "feat(protocol): checksum8 helper with manual test vectors"
```

---

## Task 5: Protocol — build_frame

**Files:**
- Modify: `mks_servo/protocol.py`
- Modify: `tests/test_protocol.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_protocol.py`:
```python
from mks_servo.protocol import build_frame


def test_build_frame_calibrate():
    """Manual §4 example: 'FA 01 80 00 7B'."""
    assert build_frame(addr=0x01, code=0x80, data=b"\x00") == bytes.fromhex("FA 01 80 00 7B")


def test_build_frame_no_data():
    """Read encoder, no data: FA 01 30 2B."""
    assert build_frame(addr=0x01, code=0x30) == bytes.fromhex("FA 01 30 2B")


def test_build_frame_speed_mode():
    """Manual §7.4: 'FA 01 F6 01 40 02 34' (dir=CW, speed=320, acc=2)."""
    assert build_frame(0x01, 0xF6, b"\x01\x40\x02") == bytes.fromhex("FA 01 F6 01 40 02 34")


def test_build_frame_rejects_addr_out_of_range():
    with pytest.raises(ValueError):
        build_frame(addr=256, code=0x30)


def test_build_frame_rejects_code_out_of_range():
    with pytest.raises(ValueError):
        build_frame(addr=1, code=300)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_protocol.py -v`
Expected: FAIL on `build_frame` import.

- [ ] **Step 3: Implement build_frame**

Append to `mks_servo/protocol.py`:
```python
from .constants import HEAD_DOWN


def build_frame(addr: int, code: int, data: bytes = b"") -> bytes:
    """Build a downlink frame: HEAD_DOWN | addr | code | data | checksum8."""
    if not 0 <= addr <= 0xFF:
        raise ValueError(f"addr must be 0..255, got {addr}")
    if not 0 <= code <= 0xFF:
        raise ValueError(f"code must be 0..255, got {code}")
    body = bytes([HEAD_DOWN, addr, code]) + data
    return body + bytes([checksum8(body)])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_protocol.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/protocol.py tests/test_protocol.py
git commit -m "feat(protocol): build_frame with manual test vectors"
```

---

## Task 6: Protocol — parse_frame

**Files:**
- Modify: `mks_servo/protocol.py`
- Modify: `tests/test_protocol.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_protocol.py`:
```python
from mks_servo.protocol import parse_frame
from mks_servo.exceptions import ChecksumError, ProtocolError


def test_parse_frame_encoder_response():
    """Manual §7.3: 'FB 01 30 FF FF FF FF 22 69 B3'."""
    addr, code, payload = parse_frame(bytes.fromhex("FB 01 30 FF FF FF FF 22 69 B3"))
    assert addr == 0x01
    assert code == 0x30
    assert payload == bytes.fromhex("FF FF FF FF 22 69")


def test_parse_frame_status_only():
    """Calibrate response: 'FB 01 80 01 7D'."""
    addr, code, payload = parse_frame(bytes.fromhex("FB 01 80 01 7D"))
    assert (addr, code, payload) == (0x01, 0x80, b"\x01")


def test_parse_frame_bad_checksum():
    bad = bytes.fromhex("FB 01 80 01 00")  # last byte should be 0x7D
    with pytest.raises(ChecksumError):
        parse_frame(bad)


def test_parse_frame_bad_header():
    with pytest.raises(ProtocolError):
        parse_frame(bytes.fromhex("AA 01 80 01 00"))


def test_parse_frame_too_short():
    with pytest.raises(ProtocolError):
        parse_frame(bytes.fromhex("FB 01"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_protocol.py -v`
Expected: FAIL on `parse_frame` import.

- [ ] **Step 3: Implement parse_frame**

Append to `mks_servo/protocol.py`:
```python
from .constants import HEAD_UP
from .exceptions import ChecksumError, ProtocolError


def parse_frame(buf: bytes) -> tuple[int, int, bytes]:
    """Parse an uplink frame. Returns (addr, code, payload)."""
    if len(buf) < 4:
        raise ProtocolError(f"frame too short: {len(buf)} bytes")
    if buf[0] != HEAD_UP:
        raise ProtocolError(f"bad uplink head: 0x{buf[0]:02X} (expected 0x{HEAD_UP:02X})")
    body, given_crc = buf[:-1], buf[-1]
    expected_crc = checksum8(body)
    if given_crc != expected_crc:
        raise ChecksumError(f"checksum mismatch: got 0x{given_crc:02X}, expected 0x{expected_crc:02X}")
    return body[1], body[2], bytes(body[3:])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_protocol.py -v`
Expected: 14 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/protocol.py tests/test_protocol.py
git commit -m "feat(protocol): parse_frame with header/checksum validation"
```

---

## Task 7: Protocol — transact (mocked serial)

**Files:**
- Modify: `mks_servo/protocol.py`
- Modify: `tests/test_protocol.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_protocol.py`:
```python
from unittest.mock import MagicMock
from mks_servo.protocol import transact
from mks_servo.exceptions import CommTimeout


def _fake_serial(reply: bytes):
    ser = MagicMock()
    ser.read.return_value = reply
    ser.in_waiting = len(reply)
    return ser


def test_transact_round_trip():
    ser = _fake_serial(bytes.fromhex("FB 01 80 01 7D"))
    payload = transact(ser, addr=1, code=0x80, data=b"\x00", expect_payload_len=1, timeout=0.1)
    assert payload == b"\x01"
    sent = ser.write.call_args[0][0]
    assert sent == bytes.fromhex("FA 01 80 00 7B")


def test_transact_timeout():
    ser = _fake_serial(b"")  # no reply
    with pytest.raises(CommTimeout):
        transact(ser, addr=1, code=0x30, expect_payload_len=6, timeout=0.05)


def test_transact_truncated_response():
    ser = _fake_serial(bytes.fromhex("FB 01"))  # only 2 bytes
    with pytest.raises(CommTimeout):
        transact(ser, addr=1, code=0x80, data=b"\x00", expect_payload_len=1, timeout=0.05)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_protocol.py -v`
Expected: FAIL on `transact` import.

- [ ] **Step 3: Implement transact**

Append to `mks_servo/protocol.py`:
```python
import time


def transact(
    ser,
    addr: int,
    code: int,
    data: bytes = b"",
    expect_payload_len: int | None = None,
    timeout: float = 0.5,
) -> bytes:
    """Send a frame and read back the matching uplink frame.

    Returns the payload (bytes between code and checksum).
    Raises CommTimeout if no full frame arrives within timeout.
    """
    request = build_frame(addr, code, data)
    ser.reset_input_buffer() if hasattr(ser, "reset_input_buffer") else None
    ser.write(request)
    if hasattr(ser, "flush"):
        ser.flush()

    if expect_payload_len is None:
        # Best effort: read whatever is available; the caller knows the layout.
        # Default to 8-byte read with timeout.
        expect_payload_len = 5
    expected_total = 4 + expect_payload_len  # head+addr+code+payload+crc

    deadline = time.monotonic() + timeout
    buf = bytearray()
    while len(buf) < expected_total:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise CommTimeout(
                f"only {len(buf)}/{expected_total} bytes received before {timeout}s timeout"
            )
        ser.timeout = remaining
        chunk = ser.read(expected_total - len(buf))
        if not chunk:
            raise CommTimeout(
                f"only {len(buf)}/{expected_total} bytes received before {timeout}s timeout"
            )
        buf.extend(chunk)

    _, _, payload = parse_frame(bytes(buf))
    return payload
```

Add the import at top of `mks_servo/protocol.py`:
```python
from .exceptions import CommTimeout
```
(merge with existing `from .exceptions import ChecksumError, ProtocolError` line.)

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_protocol.py -v`
Expected: 17 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/protocol.py tests/test_protocol.py
git commit -m "feat(protocol): transact() with timeout and frame parsing"
```

---

## Task 8: Driver — skeleton + context manager

**Files:**
- Create: `mks_servo/driver.py`
- Create: `tests/test_driver_read.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_driver_read.py`:
```python
from unittest.mock import MagicMock, patch
import pytest
from mks_servo.driver import MKSServo42D


@pytest.fixture
def fake_serial(mocker):
    """Patch serial.Serial to return a MagicMock; tests configure its .read return."""
    fake = MagicMock()
    fake.in_waiting = 0
    mocker.patch("mks_servo.driver.serial.Serial", return_value=fake)
    return fake


def test_driver_opens_serial_with_correct_params(fake_serial):
    m = MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1)
    m.open()
    from mks_servo import driver as drv
    drv.serial.Serial.assert_called_once_with(
        port="/dev/ttyUSB0", baudrate=38400, bytesize=8, parity="N", stopbits=1, timeout=0.5,
    )


def test_driver_context_manager_closes_serial(fake_serial):
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m._ser is fake_serial
    fake_serial.close.assert_called_once()


def test_driver_context_manager_disables_motor_on_exit(fake_serial):
    """Safety: __exit__ must send enable=0 if the motor was enabled."""
    fake_serial.read.return_value = bytes.fromhex("FB 01 F3 01 F0")
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        m._enabled = True  # pretend the user called enable(True)
    # Look for an enable(False) frame: FA 01 F3 00 EE
    writes = [c.args[0] for c in fake_serial.write.call_args_list]
    assert any(w.startswith(b"\xfa\x01\xf3\x00") for w in writes)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_driver_read.py -v`
Expected: FAIL on `MKSServo42D` import.

- [ ] **Step 3: Implement driver skeleton**

Create `mks_servo/driver.py`:
```python
import serial

from . import protocol
from .constants import OpCode


class MKSServo42D:
    def __init__(self, port: str, baud: int = 38400, addr: int = 1, timeout: float = 0.5) -> None:
        self.port = port
        self.baud = baud
        self.addr = addr
        self.timeout = timeout
        self._ser: serial.Serial | None = None
        self._enabled = False

    def open(self) -> None:
        self._ser = serial.Serial(
            port=self.port,
            baudrate=self.baud,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=self.timeout,
        )

    def close(self) -> None:
        if self._enabled:
            try:
                self.enable(False)
            except Exception:
                pass
            self._enabled = False
        if self._ser is not None:
            self._ser.close()
            self._ser = None

    def __enter__(self) -> "MKSServo42D":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # Internal helper used by all command methods
    def _txn(self, code: int, data: bytes = b"", expect_payload_len: int | None = None) -> bytes:
        if self._ser is None:
            raise RuntimeError("serial not open; call .open() or use as context manager")
        return protocol.transact(
            self._ser, addr=self.addr, code=code, data=data,
            expect_payload_len=expect_payload_len, timeout=self.timeout,
        )

    def enable(self, on: bool) -> bool:
        """Enable (True) or disable (False) the motor (cmd 0xF3). Returns True on success."""
        payload = self._txn(OpCode.ENABLE, bytes([0x01 if on else 0x00]), expect_payload_len=1)
        ok = payload == b"\x01"
        if ok:
            self._enabled = on
        return ok
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_driver_read.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/driver.py tests/test_driver_read.py
git commit -m "feat(driver): MKSServo42D skeleton with context manager and enable()"
```

---

## Task 9: Driver — read_encoder + read_encoder_addition

**Files:**
- Modify: `mks_servo/driver.py`
- Modify: `tests/test_driver_read.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_driver_read.py`:
```python
def test_read_encoder_returns_carry_and_value(fake_serial):
    fake_serial.read.return_value = bytes.fromhex("FB 01 30 FF FF FF FF 22 69 B3")
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        carry, value = m.read_encoder()
    assert carry == -1
    assert value == 0x2269


def test_read_encoder_addition_returns_int48(fake_serial):
    # 6-byte payload: 0x000000007FFF (positive, < 2^47)
    # Frame: FB 01 31 00 00 00 00 7F FF + checksum
    body = bytes.fromhex("FB 01 31 00 00 00 00 7F FF")
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        value = m.read_encoder_addition()
    assert value == 0x7FFF


def test_read_encoder_addition_negative(fake_serial):
    # int48 -0x4000 -> 0xFFFFFFFFC000
    body = bytes.fromhex("FB 01 31 FF FF FF FF C0 00")
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        value = m.read_encoder_addition()
    assert value == -0x4000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_driver_read.py::test_read_encoder_returns_carry_and_value -v`
Expected: FAIL with `AttributeError: ... has no attribute 'read_encoder'`.

- [ ] **Step 3: Implement read_encoder + read_encoder_addition**

Append to `MKSServo42D` class in `mks_servo/driver.py`:
```python
    def read_encoder(self) -> tuple[int, int]:
        """Cmd 0x30: returns (carry int32 BE, value uint16 BE in 0..0x3FFF)."""
        payload = self._txn(OpCode.READ_ENCODER, expect_payload_len=6)
        carry = int.from_bytes(payload[0:4], "big", signed=True)
        value = int.from_bytes(payload[4:6], "big", signed=False)
        return carry, value

    def read_encoder_addition(self) -> int:
        """Cmd 0x31: cumulative encoder value (int48 BE). 0x4000 per CW turn."""
        payload = self._txn(OpCode.READ_ENCODER_ADDITION, expect_payload_len=6)
        return int.from_bytes(payload, "big", signed=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_driver_read.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/driver.py tests/test_driver_read.py
git commit -m "feat(driver): read_encoder + read_encoder_addition"
```

---

## Task 10: Driver — read_speed_rpm, read_pulses, read_angle_error

**Files:**
- Modify: `mks_servo/driver.py`
- Modify: `tests/test_driver_read.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_driver_read.py`:
```python
def test_read_speed_rpm_positive(fake_serial):
    # speed = +500 RPM (CCW). Manual §5.1.3 uses code 0x32; payload is int16 BE.
    body = bytes.fromhex("FB 01 32") + (500).to_bytes(2, "big", signed=True)
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m.read_speed_rpm() == 500


def test_read_speed_rpm_negative(fake_serial):
    body = bytes.fromhex("FB 01 32") + (-1500).to_bytes(2, "big", signed=True)
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m.read_speed_rpm() == -1500


def test_read_pulses(fake_serial):
    # int32 BE, e.g. 32000
    body = bytes.fromhex("FB 01 33") + (32000).to_bytes(4, "big", signed=True)
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m.read_pulses() == 32000


def test_read_angle_error_one_degree(fake_serial):
    # Manual §5.1.7: 1 degree -> 51200/360 = 142 (rounded).
    body = bytes.fromhex("FB 01 39") + (142).to_bytes(4, "big", signed=True)
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m.read_angle_error() == 142
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_driver_read.py -v`
Expected: 4 new failures with `AttributeError`.

- [ ] **Step 3: Implement the three methods**

Append to `MKSServo42D` class:
```python
    def read_speed_rpm(self) -> int:
        """Cmd 0x32: signed RPM (>0 = CCW, <0 = CW)."""
        payload = self._txn(OpCode.READ_SPEED_RPM, expect_payload_len=2)
        return int.from_bytes(payload, "big", signed=True)

    def read_pulses(self) -> int:
        """Cmd 0x33: pulses received (int32 BE)."""
        payload = self._txn(OpCode.READ_PULSES, expect_payload_len=4)
        return int.from_bytes(payload, "big", signed=True)

    def read_angle_error(self) -> int:
        """Cmd 0x39: angle error in driver units (51200 = 360°)."""
        payload = self._txn(OpCode.READ_ANGLE_ERROR, expect_payload_len=4)
        return int.from_bytes(payload, "big", signed=True)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_driver_read.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/driver.py tests/test_driver_read.py
git commit -m "feat(driver): read_speed_rpm, read_pulses, read_angle_error"
```

---

## Task 11: Driver — read_motor_status

**Files:**
- Modify: `mks_servo/driver.py`
- Modify: `tests/test_driver_read.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_driver_read.py`:
```python
from mks_servo.driver import MotorStatus


def test_read_motor_status_stopped(fake_serial):
    body = bytes.fromhex("FB 01 F1 01")
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m.read_motor_status() == MotorStatus.STOPPED


def test_read_motor_status_full_speed(fake_serial):
    body = bytes.fromhex("FB 01 F1 04")
    crc = sum(body) & 0xFF
    fake_serial.read.return_value = body + bytes([crc])
    with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
        assert m.read_motor_status() == MotorStatus.FULL_SPEED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_driver_read.py -v`
Expected: FAIL on `MotorStatus` import.

- [ ] **Step 3: Implement MotorStatus enum + method**

At top of `mks_servo/driver.py`, after existing imports add:
```python
from enum import IntEnum


class MotorStatus(IntEnum):
    QUERY_FAIL = 0
    STOPPED = 1
    SPEED_UP = 2
    SPEED_DOWN = 3
    FULL_SPEED = 4
    HOMING = 5
    CALIBRATING = 6
```

Append to `MKSServo42D` class:
```python
    def read_motor_status(self) -> MotorStatus:
        """Cmd 0xF1: motor running status."""
        payload = self._txn(OpCode.QUERY_STATUS, expect_payload_len=1)
        return MotorStatus(payload[0])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_driver_read.py -v`
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/driver.py tests/test_driver_read.py
git commit -m "feat(driver): read_motor_status with MotorStatus enum"
```

---

## Task 12: Driver — conversion helpers

**Files:**
- Modify: `mks_servo/driver.py`
- Create: `tests/test_driver_helpers.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_driver_helpers.py`:
```python
from mks_servo.driver import (
    degrees_to_encoder_counts,
    encoder_counts_to_degrees,
    degrees_to_pulses,
)


def test_degrees_to_encoder_counts_one_full_turn():
    assert degrees_to_encoder_counts(360) == 0x4000


def test_degrees_to_encoder_counts_quarter_turn():
    assert degrees_to_encoder_counts(90) == 0x4000 // 4


def test_encoder_counts_to_degrees_inverse():
    assert encoder_counts_to_degrees(0x4000) == 360.0
    assert encoder_counts_to_degrees(-0x4000) == -360.0


def test_degrees_to_pulses_default_microsteps_16():
    # 360° at 16 microsteps = 200 * 16 = 3200 pulses
    assert degrees_to_pulses(360) == 3200


def test_degrees_to_pulses_custom_microsteps():
    assert degrees_to_pulses(360, microsteps=64) == 200 * 64
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_driver_helpers.py -v`
Expected: FAIL on imports.

- [ ] **Step 3: Implement helpers**

Append to `mks_servo/driver.py` (top-level functions, not methods):
```python
from .constants import ENCODER_COUNTS_PER_REV, NEMA17_FULL_STEPS


def degrees_to_encoder_counts(deg: float) -> int:
    return int(round(deg * ENCODER_COUNTS_PER_REV / 360))


def encoder_counts_to_degrees(counts: int) -> float:
    return counts * 360.0 / ENCODER_COUNTS_PER_REV


def degrees_to_pulses(deg: float, microsteps: int = 16) -> int:
    return int(round(deg * NEMA17_FULL_STEPS * microsteps / 360))
```

Add a method on the class to expose `read_angle_degrees`:
```python
    def read_angle_degrees(self) -> float:
        """Cumulative angle in degrees, from encoder addition."""
        return encoder_counts_to_degrees(self.read_encoder_addition())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_driver_helpers.py -v tests/test_driver_read.py -v`
Expected: 5 + 12 = 17 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/driver.py tests/test_driver_helpers.py
git commit -m "feat(driver): conversion helpers (degrees <-> counts/pulses)"
```

---

## Task 13: Driver — config commands (calibrate, restart, restore_defaults, set_zero_point, release_protection)

**Files:**
- Modify: `mks_servo/driver.py`
- Create: `tests/test_driver_config.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_driver_config.py`:
```python
from unittest.mock import MagicMock
import pytest
from mks_servo.driver import MKSServo42D
from mks_servo.exceptions import CalibrationFailed


@pytest.fixture
def fake_serial(mocker):
    fake = MagicMock()
    fake.in_waiting = 0
    mocker.patch("mks_servo.driver.serial.Serial", return_value=fake)
    return fake


def _resp(addr: int, code: int, payload: bytes) -> bytes:
    body = bytes([0xFB, addr, code]) + payload
    return body + bytes([sum(body) & 0xFF])


def test_calibrate_success(fake_serial):
    # Calibration returns status=1 (success). Some firmwares emit status=0 first; we accept final 1.
    fake_serial.read.return_value = _resp(1, 0x80, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        m.calibrate()  # no exception


def test_calibrate_fail_raises(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x80, b"\x02")  # status=2 = fail
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        with pytest.raises(CalibrationFailed):
            m.calibrate()


def test_restart_sends_correct_frame(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x41, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        m.restart()
    sent = fake_serial.write.call_args[0][0]
    assert sent[:3] == bytes.fromhex("FA 01 41")


def test_restore_defaults(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x3F, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.restore_defaults() is True


def test_set_zero_point(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x92, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.set_zero_point() is True


def test_release_protection(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x3D, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.release_protection() is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_driver_config.py -v`
Expected: FAIL on missing methods.

- [ ] **Step 3: Implement methods**

Append to `MKSServo42D` class:
```python
    def calibrate(self) -> None:
        """Cmd 0x80: calibrate the encoder. Motor MUST be unloaded.
        Raises CalibrationFailed on status=2.
        """
        payload = self._txn(OpCode.CALIBRATE, b"\x00", expect_payload_len=1)
        if payload == b"\x02":
            raise CalibrationFailed("driver returned status=2 (calibration fail)")

    def restart(self) -> bool:
        payload = self._txn(OpCode.RESTART, expect_payload_len=1)
        return payload == b"\x01"

    def restore_defaults(self) -> bool:
        """⚠ wipes calibration and config. Requires re-calibration after."""
        payload = self._txn(OpCode.RESTORE_DEFAULTS, expect_payload_len=1)
        return payload == b"\x01"

    def set_zero_point(self) -> bool:
        """Cmd 0x92: set the current axis to 0 ('go-home without movement')."""
        payload = self._txn(OpCode.SET_ZERO_POINT, expect_payload_len=1)
        return payload == b"\x01"

    def release_protection(self) -> bool:
        """Cmd 0x3D: clear stall-protection latch."""
        payload = self._txn(OpCode.RELEASE_PROTECTION, expect_payload_len=1)
        return payload == b"\x01"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_driver_config.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/driver.py tests/test_driver_config.py
git commit -m "feat(driver): config commands (calibrate, restart, restore, zero, release)"
```

---

## Task 14: Driver — set_work_mode, set_work_current_ma, set_subdivision

**Files:**
- Modify: `mks_servo/driver.py`
- Modify: `tests/test_driver_config.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_driver_config.py`:
```python
from mks_servo.constants import WorkMode


def test_set_work_mode_sends_correct_byte(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x82, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.set_work_mode(WorkMode.SR_vFOC) is True
    sent = fake_serial.write.call_args[0][0]
    assert sent[:4] == bytes.fromhex("FA 01 82 05")  # SR_vFOC = 5


def test_set_work_current_ma_encodes_uint16_be(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x83, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.set_work_current_ma(1600) is True
    sent = fake_serial.write.call_args[0][0]
    # 1600 = 0x0640
    assert sent[:5] == bytes.fromhex("FA 01 83 06 40")


def test_set_work_current_ma_clamps_max(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x83, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        with pytest.raises(ValueError):
            m.set_work_current_ma(5000)  # SERVO42D max is 3000


def test_set_subdivision(fake_serial):
    fake_serial.read.return_value = _resp(1, 0x84, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.set_subdivision(64) is True
    sent = fake_serial.write.call_args[0][0]
    assert sent[:4] == bytes.fromhex("FA 01 84 40")


def test_set_subdivision_rejects_zero(fake_serial):
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        with pytest.raises(ValueError):
            m.set_subdivision(0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_driver_config.py -v`
Expected: 5 new failures.

- [ ] **Step 3: Implement methods**

Append to `MKSServo42D` class:
```python
    def set_work_mode(self, mode) -> bool:
        """Cmd 0x82: set work mode."""
        payload = self._txn(OpCode.SET_WORK_MODE, bytes([int(mode)]), expect_payload_len=1)
        return payload == b"\x01"

    def set_work_current_ma(self, current_ma: int) -> bool:
        """Cmd 0x83: working current in mA. SERVO42D max = 3000, must be > 0."""
        if not 0 < current_ma <= 3000:
            raise ValueError(f"current_ma must be 1..3000 (SERVO42D), got {current_ma}")
        data = current_ma.to_bytes(2, "big", signed=False)
        payload = self._txn(OpCode.SET_WORK_CURRENT, data, expect_payload_len=1)
        return payload == b"\x01"

    def set_subdivision(self, microsteps: int) -> bool:
        """Cmd 0x84: microsteps. 1..256 (256 sent as 0x00 by manual convention).
        Note: many subdivisions are valid; we let the driver validate.
        """
        if not 1 <= microsteps <= 256:
            raise ValueError(f"microsteps must be 1..256, got {microsteps}")
        byte_val = 0x00 if microsteps == 256 else microsteps
        payload = self._txn(OpCode.SET_SUBDIVISION, bytes([byte_val]), expect_payload_len=1)
        return payload == b"\x01"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_driver_config.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/driver.py tests/test_driver_config.py
git commit -m "feat(driver): set_work_mode, set_work_current_ma, set_subdivision"
```

---

## Task 15: Driver — read_all_config

**Files:**
- Modify: `mks_servo/driver.py`
- Modify: `tests/test_driver_config.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_driver_config.py`:
```python
def test_read_all_config_returns_dict(fake_serial):
    """Manual §5.9: read 0x47, response is FB 01 47 + 34 bytes payload + CRC."""
    # Build a known-good 34-byte config payload following the manual's table:
    # bytes 4..37 of the response (so 34 total).
    payload = bytearray(34)
    payload[0] = 5    # mode = SR_vFOC
    payload[1] = 0x06; payload[2] = 0x40  # current = 1600 mA (uint16 BE)
    payload[3] = 4    # hold = 50%
    payload[4] = 0x10  # subdivision = 16
    payload[5] = 0    # En = active low
    payload[6] = 0    # Dir = CW
    # Remaining bytes leave at 0 for this test
    body = bytes([0xFB, 0x01, 0x47]) + bytes(payload)
    fake_serial.read.return_value = body + bytes([sum(body) & 0xFF])

    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        cfg = m.read_all_config()

    assert cfg["mode"] == 5
    assert cfg["current_ma"] == 1600
    assert cfg["subdivision"] == 16
    assert isinstance(cfg["raw"], bytes) and len(cfg["raw"]) == 34
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_driver_config.py::test_read_all_config_returns_dict -v`
Expected: FAIL with `AttributeError`.

- [ ] **Step 3: Implement read_all_config**

Append to `MKSServo42D` class:
```python
    def read_all_config(self) -> dict:
        """Cmd 0x47: read 38-byte config snapshot.
        Returns a dict with parsed common fields plus raw bytes for full diff.
        Layout per manual §5.9 table (bytes 4..37 of the response = our payload bytes 0..33).
        """
        payload = self._txn(OpCode.READ_ALL_CONFIG, expect_payload_len=34)
        return {
            "mode": payload[0],
            "current_ma": int.from_bytes(payload[1:3], "big"),
            "hold_current_pct_idx": payload[3],
            "subdivision": 256 if payload[4] == 0 else payload[4],
            "en_active": payload[5],
            "dir_cw": payload[6] == 0,
            "auto_screen_off": bool(payload[7]),
            "stall_protect": bool(payload[8]),
            "interp_enabled": bool(payload[9]),
            "baud_code": payload[10],
            "slave_addr": payload[11],
            "raw": bytes(payload),
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_driver_config.py -v`
Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/driver.py tests/test_driver_config.py
git commit -m "feat(driver): read_all_config snapshot (cmd 0x47)"
```

---

## Task 16: Driver — motion: emergency_stop, move_speed, save_speed_mode_state

**Files:**
- Modify: `mks_servo/driver.py`
- Create: `tests/test_driver_motion.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_driver_motion.py`:
```python
from unittest.mock import MagicMock
import pytest
from mks_servo.driver import MKSServo42D
from mks_servo.constants import Direction


@pytest.fixture
def fake_serial(mocker):
    fake = MagicMock()
    fake.in_waiting = 0
    mocker.patch("mks_servo.driver.serial.Serial", return_value=fake)
    return fake


def _resp(addr: int, code: int, payload: bytes) -> bytes:
    body = bytes([0xFB, addr, code]) + payload
    return body + bytes([sum(body) & 0xFF])


def test_emergency_stop(fake_serial):
    fake_serial.read.return_value = _resp(1, 0xF7, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.emergency_stop() is True
    sent = fake_serial.write.call_args[0][0]
    assert sent[:3] == bytes.fromhex("FA 01 F7")


def test_move_speed_320rpm_cw_acc2(fake_serial):
    """Manual §7.4: 'FA 01 F6 01 40 02' for dir=CW, speed=320, acc=2."""
    fake_serial.read.return_value = _resp(1, 0xF6, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.move_speed(rpm=320, acc=2, direction=Direction.CW) is True
    sent = fake_serial.write.call_args[0][0]
    assert sent == bytes.fromhex("FA 01 F6 01 40 02 34")


def test_move_speed_ccw_negative_dir_bit(fake_serial):
    """Manual §6.5: bit7 of byte4 is dir; 0x81 = CCW + speed bits."""
    fake_serial.read.return_value = _resp(1, 0xF6, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        m.move_speed(rpm=320, acc=2, direction=Direction.CCW)
    sent = fake_serial.write.call_args[0][0]
    # CCW + speed=320 (0x140) -> byte4 = 0x81, byte5 = 0x40
    assert sent == bytes.fromhex("FA 01 F6 81 40 02 B4")


def test_move_speed_clamps_rpm(fake_serial):
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        with pytest.raises(ValueError):
            m.move_speed(rpm=4000, acc=2, direction=Direction.CW)


def test_save_speed_mode_state_save(fake_serial):
    fake_serial.read.return_value = _resp(1, 0xFF, b"\x02")  # 2 = success
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        assert m.save_speed_mode_state(save=True) is True
    sent = fake_serial.write.call_args[0][0]
    assert sent[:4] == bytes.fromhex("FA 01 FF C8")


def test_save_speed_mode_state_clean(fake_serial):
    fake_serial.read.return_value = _resp(1, 0xFF, b"\x02")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        m.save_speed_mode_state(save=False)
    sent = fake_serial.write.call_args[0][0]
    assert sent[:4] == bytes.fromhex("FA 01 FF CA")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_driver_motion.py -v`
Expected: 6 failures (missing methods).

- [ ] **Step 3: Implement motion methods**

Append to `MKSServo42D` class:
```python
    def emergency_stop(self) -> bool:
        """Cmd 0xF7: stop everything immediately. ⚠ above 1000 RPM use stop_speed_mode instead."""
        payload = self._txn(OpCode.EMERGENCY_STOP, expect_payload_len=1)
        return payload == b"\x01"

    def move_speed(self, rpm: int, acc: int = 2, direction=None) -> bool:
        """Cmd 0xF6: continuous speed mode.

        rpm: 0..3000 (saturates at mode max)
        acc: 0..255 (0 = no ramp, instant)
        direction: Direction.CW (default) or Direction.CCW
        """
        from .constants import Direction as _Dir
        if direction is None:
            direction = _Dir.CW
        if not 0 <= rpm <= 3000:
            raise ValueError(f"rpm must be 0..3000, got {rpm}")
        if not 0 <= acc <= 255:
            raise ValueError(f"acc must be 0..255, got {acc}")
        # Byte4 = dir<<7 | (speed >> 8); Byte5 = speed & 0xFF
        dir_bit = 0x80 if direction == _Dir.CCW else 0x00
        b4 = dir_bit | ((rpm >> 8) & 0x0F)
        b5 = rpm & 0xFF
        payload = self._txn(OpCode.MOVE_SPEED, bytes([b4, b5, acc]), expect_payload_len=1)
        return payload == b"\x01"

    def save_speed_mode_state(self, save: bool = True) -> bool:
        """Cmd 0xFF: save (state=0xC8) or clean (state=0xCA) the speed-mode params.

        After save, on power-up the motor will resume the saved speed automatically.
        """
        state = 0xC8 if save else 0xCA
        payload = self._txn(OpCode.SAVE_SPEED_STATE, bytes([state]), expect_payload_len=1)
        # Manual: status=2 = success.
        return payload == b"\x02"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_driver_motion.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/driver.py tests/test_driver_motion.py
git commit -m "feat(driver): emergency_stop, move_speed, save_speed_mode_state"
```

---

## Task 17: Driver — position by pulses (relative + absolute)

**Files:**
- Modify: `mks_servo/driver.py`
- Modify: `tests/test_driver_motion.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_driver_motion.py`:
```python
def test_move_relative_pulses_manual_example(fake_serial):
    """Manual §7.5: 'FA 01 FD 02 80 05 00 09 C4 00 4C' = reverse 200 turns at 640 RPM, acc=5,
    16 microsteps -> 200*200*16 = 640000 pulses = 0x9C400.
    But the docstring example uses 200 turns x 16 microsteps... we test a simpler vector here."""
    # Test with rpm=320, acc=2, dir=CW, pulses=250 (0xFA = 250 in 4 bytes).
    fake_serial.read.return_value = _resp(1, 0xFD, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        m.move_relative_pulses(pulses=250, rpm=320, acc=2, direction=Direction.CW)
    sent = fake_serial.write.call_args[0][0]
    # FA 01 FD 01 40 02 00 00 00 FA <crc>
    expected_body = bytes.fromhex("FA 01 FD 01 40 02 00 00 00 FA")
    assert sent[:-1] == expected_body


def test_move_relative_pulses_ccw(fake_serial):
    fake_serial.read.return_value = _resp(1, 0xFD, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        m.move_relative_pulses(pulses=250, rpm=320, acc=2, direction=Direction.CCW)
    sent = fake_serial.write.call_args[0][0]
    # CCW dir bit set on byte4
    assert sent[3] & 0x80 == 0x80


def test_move_absolute_pulses_negative(fake_serial):
    """Manual §6.7: target -0x4000 pulses, speed=600, acc=2.
    Frame: FA 01 FE 02 58 02 FF FF C0 00 <crc>."""
    fake_serial.read.return_value = _resp(1, 0xFE, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        m.move_absolute_pulses(pulses=-0x4000, rpm=600, acc=2)
    sent = fake_serial.write.call_args[0][0]
    expected_body = bytes.fromhex("FA 01 FE 02 58 02 FF FF C0 00")
    assert sent[:-1] == expected_body
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_driver_motion.py -v`
Expected: 3 failures.

- [ ] **Step 3: Implement methods**

Append to `MKSServo42D` class:
```python
    def move_relative_pulses(self, pulses: int, rpm: int, acc: int = 2, direction=None) -> bool:
        """Cmd 0xFD: relative move by pulse count.

        pulses: 0..0xFFFFFFFF (sign comes from `direction`)
        rpm: 0..3000
        acc: 0..255
        """
        from .constants import Direction as _Dir
        if direction is None:
            direction = _Dir.CW
        if not 0 <= pulses <= 0xFFFFFFFF:
            raise ValueError(f"pulses must be 0..2^32-1, got {pulses}")
        if not 0 <= rpm <= 3000:
            raise ValueError(f"rpm must be 0..3000, got {rpm}")
        if not 0 <= acc <= 255:
            raise ValueError(f"acc must be 0..255, got {acc}")
        dir_bit = 0x80 if direction == _Dir.CCW else 0x00
        b4 = dir_bit | ((rpm >> 8) & 0x0F)
        b5 = rpm & 0xFF
        data = bytes([b4, b5, acc]) + pulses.to_bytes(4, "big", signed=False)
        payload = self._txn(OpCode.MOVE_REL_PULSES, data, expect_payload_len=1)
        return payload == b"\x01"

    def move_absolute_pulses(self, pulses: int, rpm: int, acc: int = 2) -> bool:
        """Cmd 0xFE: absolute move to a signed pulse coordinate (int32 BE)."""
        if not -(2**31) <= pulses <= 2**31 - 1:
            raise ValueError(f"pulses out of int32 range: {pulses}")
        if not 0 <= rpm <= 3000:
            raise ValueError(f"rpm must be 0..3000, got {rpm}")
        if not 0 <= acc <= 255:
            raise ValueError(f"acc must be 0..255, got {acc}")
        speed_bytes = rpm.to_bytes(2, "big", signed=False)
        data = speed_bytes + bytes([acc]) + pulses.to_bytes(4, "big", signed=True)
        payload = self._txn(OpCode.MOVE_ABS_PULSES, data, expect_payload_len=1)
        return payload == b"\x01"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_driver_motion.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/driver.py tests/test_driver_motion.py
git commit -m "feat(driver): move_relative_pulses, move_absolute_pulses"
```

---

## Task 18: Driver — position by encoder axis (relative + absolute)

**Files:**
- Modify: `mks_servo/driver.py`
- Modify: `tests/test_driver_motion.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_driver_motion.py`:
```python
def test_move_absolute_axis_manual_example(fake_serial):
    """Manual §6.9: 'FA 01 F5 02 58 02 00 00 40 00 8C' for abs=0x4000, speed=600, acc=2."""
    fake_serial.read.return_value = _resp(1, 0xF5, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        m.move_absolute_axis(counts=0x4000, rpm=600, acc=2)
    sent = fake_serial.write.call_args[0][0]
    expected_body = bytes.fromhex("FA 01 F5 02 58 02 00 00 40 00")
    assert sent[:-1] == expected_body


def test_move_relative_axis_negative(fake_serial):
    """Manual §6.8: relAxis=-0x4000, speed=600, acc=2."""
    fake_serial.read.return_value = _resp(1, 0xF4, b"\x01")
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        m.move_relative_axis(counts=-0x4000, rpm=600, acc=2)
    sent = fake_serial.write.call_args[0][0]
    expected_body = bytes.fromhex("FA 01 F4 02 58 02 FF FF C0 00")
    assert sent[:-1] == expected_body
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_driver_motion.py -v`
Expected: 2 failures.

- [ ] **Step 3: Implement methods**

Append to `MKSServo42D` class:
```python
    def move_relative_axis(self, counts: int, rpm: int, acc: int = 2) -> bool:
        """Cmd 0xF4: relative move by encoder counts (int32 BE). 0x4000 = 1 turn."""
        if not -(2**31) <= counts <= 2**31 - 1:
            raise ValueError(f"counts out of int32 range: {counts}")
        if not 0 <= rpm <= 3000:
            raise ValueError(f"rpm must be 0..3000, got {rpm}")
        if not 0 <= acc <= 255:
            raise ValueError(f"acc must be 0..255, got {acc}")
        data = rpm.to_bytes(2, "big") + bytes([acc]) + counts.to_bytes(4, "big", signed=True)
        payload = self._txn(OpCode.MOVE_REL_AXIS, data, expect_payload_len=1)
        return payload == b"\x01"

    def move_absolute_axis(self, counts: int, rpm: int, acc: int = 2) -> bool:
        """Cmd 0xF5: absolute move to encoder count (int32 BE). Supports real-time updates."""
        if not -(2**31) <= counts <= 2**31 - 1:
            raise ValueError(f"counts out of int32 range: {counts}")
        if not 0 <= rpm <= 3000:
            raise ValueError(f"rpm must be 0..3000, got {rpm}")
        if not 0 <= acc <= 255:
            raise ValueError(f"acc must be 0..255, got {acc}")
        data = rpm.to_bytes(2, "big") + bytes([acc]) + counts.to_bytes(4, "big", signed=True)
        payload = self._txn(OpCode.MOVE_ABS_AXIS, data, expect_payload_len=1)
        return payload == b"\x01"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_driver_motion.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add mks_servo/driver.py tests/test_driver_motion.py
git commit -m "feat(driver): move_relative_axis, move_absolute_axis"
```

---

## Task 19: Driver — wait_until_idle

**Files:**
- Modify: `mks_servo/driver.py`
- Modify: `tests/test_driver_motion.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_driver_motion.py`:
```python
def test_wait_until_idle_returns_when_stopped(fake_serial):
    """Driver returns FULL_SPEED twice then STOPPED — wait_until_idle must finish."""
    fake_serial.read.side_effect = [
        _resp(1, 0xF1, b"\x04"),  # FULL_SPEED
        _resp(1, 0xF1, b"\x04"),
        _resp(1, 0xF1, b"\x01"),  # STOPPED
    ]
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        m.wait_until_idle(timeout=2.0, poll_interval=0.0)


def test_wait_until_idle_raises_on_timeout(fake_serial):
    fake_serial.read.return_value = _resp(1, 0xF1, b"\x04")  # always FULL_SPEED
    from mks_servo.exceptions import CommTimeout, MKSError
    with MKSServo42D("/dev/ttyUSB0", 38400, 1) as m:
        with pytest.raises(MKSError):
            m.wait_until_idle(timeout=0.1, poll_interval=0.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_driver_motion.py -v`
Expected: 2 failures.

- [ ] **Step 3: Implement wait_until_idle**

Add the import at top of `mks_servo/driver.py`:
```python
import time
```

Append to `MKSServo42D` class:
```python
    def wait_until_idle(self, timeout: float = 10.0, poll_interval: float = 0.05) -> None:
        """Poll cmd 0xF1 until status returns to STOPPED (or HOMING/CALIBRATING done).

        Raises MotorFault if timeout is exceeded.
        """
        from .exceptions import MotorFault
        deadline = time.monotonic() + timeout
        while True:
            st = self.read_motor_status()
            if st == MotorStatus.STOPPED:
                return
            if time.monotonic() >= deadline:
                raise MotorFault(f"motor still {st.name} after {timeout}s")
            if poll_interval > 0:
                time.sleep(poll_interval)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_driver_motion.py -v && pytest -v`
Expected: 13 motion tests pass; full suite passes (~40 tests, no failures).

- [ ] **Step 5: Commit**

```bash
git add mks_servo/driver.py tests/test_driver_motion.py
git commit -m "feat(driver): wait_until_idle (poll cmd 0xF1)"
```

---

## Task 20: Benchmark common helpers (`_common.py`)

**Files:**
- Create: `benchmarks/__init__.py` (empty)
- Create: `benchmarks/_common.py`

- [ ] **Step 1: Create `benchmarks/__init__.py`**

Empty file.

- [ ] **Step 2: Implement `_common.py`**

Create `benchmarks/_common.py`:
```python
"""Shared helpers for benchmark scripts: config loading, output dirs, CSV/log writers."""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import tomllib  # py >= 3.11
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_ROOT = REPO_ROOT / "results"
CONFIG_PATH = REPO_ROOT / "config.toml"


def load_config() -> dict:
    with CONFIG_PATH.open("rb") as f:
        return tomllib.load(f)


def make_run_dir(bench_name: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = RESULTS_ROOT / f"{bench_name}_{ts}"
    (d / "plots").mkdir(parents=True, exist_ok=True)
    return d


def open_csv(path: Path, fieldnames: list[str]):
    f = path.open("w", newline="")
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    return f, w


def append_jsonl(path: Path, record: dict) -> None:
    with path.open("a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def banner(msg: str) -> None:
    print(f"\n=== {msg} ===", flush=True)


def confirm(prompt: str) -> None:
    """Pause for manual user action (used by persistence tests)."""
    print(f"\n[ACTION REQUIRED] {prompt}", flush=True)
    input("Press ENTER when done...")
```

- [ ] **Step 3: Smoke-import test**

Run: `python -c "from benchmarks._common import load_config; print(load_config()['serial']['baud'])"`
Expected: prints `38400`.

- [ ] **Step 4: Commit**

```bash
git add benchmarks/__init__.py benchmarks/_common.py
git commit -m "feat(benchmarks): _common.py (config, run dirs, CSV/JSONL helpers)"
```

---

## Task 21: Benchmark `01_smoke.py` — sanity check & one-time calibration

**Files:**
- Create: `benchmarks/01_smoke.py`

- [ ] **Step 1: Implement smoke benchmark**

Create `benchmarks/01_smoke.py`:
```python
"""01_smoke: verify communication, dump config, optionally calibrate.

Usage: python benchmarks/01_smoke.py [--calibrate]
Hardware required.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mks_servo import MKSServo42D, MotorStatus
from mks_servo.constants import WorkMode
from benchmarks._common import banner, load_config, make_run_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibrate", action="store_true",
                        help="Run encoder calibration (motor MUST be unloaded)")
    args = parser.parse_args()

    cfg = load_config()
    run_dir = make_run_dir("smoke")
    print(f"Output dir: {run_dir}")

    with MKSServo42D(
        port=cfg["serial"]["port"],
        baud=cfg["serial"]["baud"],
        addr=cfg["serial"]["slave_addr"],
        timeout=cfg["serial"]["timeout"],
    ) as m:
        banner("Step 1: ping (read encoder)")
        carry, value = m.read_encoder()
        print(f"  encoder: carry={carry}, value=0x{value:04X} ({value})")

        banner("Step 2: read full config snapshot")
        snap = m.read_all_config()
        print(json.dumps({k: v for k, v in snap.items() if k != "raw"}, indent=2))
        (run_dir / "config_snapshot.json").write_text(
            json.dumps({**{k: v for k, v in snap.items() if k != "raw"},
                        "raw_hex": snap["raw"].hex()}, indent=2)
        )

        banner("Step 3: motor status")
        print(f"  status = {m.read_motor_status().name}")

        banner("Step 4: ensure SR_vFOC mode + 16 microsteps")
        m.set_work_mode(WorkMode.SR_vFOC)
        m.set_subdivision(16)

        if args.calibrate:
            banner("Step 5: CALIBRATING (motor must be unloaded)")
            m.calibrate()
            print("  calibration OK (re-read config to verify):")
            print(json.dumps({k: v for k, v in m.read_all_config().items() if k != "raw"}, indent=2))
        else:
            print("  (skipping calibration; pass --calibrate to run it)")

    print(f"\nSmoke OK. Artifacts in {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Add `__init__.py` re-exports**

Edit `mks_servo/__init__.py`:
```python
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
```

- [ ] **Step 3: Hardware run (HIL)**

⚠ This is a hardware step. With the motor connected (12V on V+, USB-RS485 on A/B):

Run: `python benchmarks/01_smoke.py`
Expected: prints encoder value, config snapshot, status STOPPED. No exceptions.

If `--calibrate` is passed and the motor is **mechanically unloaded**, calibration succeeds.

- [ ] **Step 4: Commit**

```bash
git add benchmarks/01_smoke.py mks_servo/__init__.py
git commit -m "feat(benchmarks): 01_smoke.py (ping + config dump + optional calibrate)"
```

---

## Task 22: Benchmark P1 — repeatability (`02_precision.py` part 1)

**Files:**
- Create: `benchmarks/02_precision.py`

- [ ] **Step 1: Implement P1 only (skeleton + repeatability)**

Create `benchmarks/02_precision.py`:
```python
"""02_precision: precision benchmarks (P1, P3, P5 + V1).

Usage: python benchmarks/02_precision.py [--tests P1,P3,P5,V1] [--iters N]
Default runs all four. Hardware required.
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from mks_servo import MKSServo42D
from mks_servo.constants import WorkMode
from mks_servo.driver import (
    degrees_to_encoder_counts,
    encoder_counts_to_degrees,
)
from benchmarks._common import banner, load_config, make_run_dir


def _setup(m: MKSServo42D) -> None:
    m.set_work_mode(WorkMode.SR_vFOC)
    m.set_subdivision(16)
    m.enable(True)


def run_p1(m: MKSServo42D, run_dir: Path, iters: int = 100) -> None:
    """P1: repeatability — return to 90° from a random angle, measure residual."""
    banner(f"P1: repeatability (iters={iters})")
    target_deg = 90.0
    target_counts = degrees_to_encoder_counts(target_deg)
    csv_path = run_dir / "p1_repeatability.csv"

    rows = []
    for i in range(iters):
        # 1) move to a random angle in [-180, 180)
        rand_deg = random.uniform(-180.0, 180.0)
        m.move_absolute_axis(degrees_to_encoder_counts(rand_deg), rpm=300, acc=10)
        m.wait_until_idle(timeout=10.0)

        # 2) move to target
        m.move_absolute_axis(target_counts, rpm=300, acc=10)
        m.wait_until_idle(timeout=10.0)

        # 3) read measured angle
        measured_counts = m.read_encoder_addition()
        measured_deg = encoder_counts_to_degrees(measured_counts)
        residual_deg = measured_deg - target_deg
        rows.append({
            "iter": i,
            "rand_deg": rand_deg,
            "target_deg": target_deg,
            "measured_deg": measured_deg,
            "residual_deg": residual_deg,
        })
        if (i + 1) % 10 == 0:
            print(f"  iter {i+1}/{iters}: residual={residual_deg:+.4f}°")

    # write CSV
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # stats
    residuals = np.array([r["residual_deg"] for r in rows])
    sigma = float(np.std(residuals, ddof=1))
    peak = float(np.max(np.abs(residuals)))
    print(f"  σ = {sigma:.4f}°,  peak = {peak:.4f}°")

    # plot histogram
    fig, ax = plt.subplots()
    ax.hist(residuals, bins=30)
    ax.set_xlabel("residual [deg]")
    ax.set_ylabel("count")
    ax.set_title(f"P1 repeatability  σ={sigma:.4f}°  peak={peak:.4f}°  (n={iters})")
    fig.tight_layout()
    fig.savefig(run_dir / "plots" / "p1_repeatability_hist.png", dpi=120)
    plt.close(fig)
    print(f"  → {csv_path.name} + p1_repeatability_hist.png")


TEST_FUNCS = {"P1": run_p1}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests", default="P1", help="Comma-separated test ids")
    parser.add_argument("--iters", type=int, default=100)
    args = parser.parse_args()

    cfg = load_config()
    run_dir = make_run_dir("precision")
    print(f"Output dir: {run_dir}")

    requested = [t.strip().upper() for t in args.tests.split(",")]
    with MKSServo42D(
        port=cfg["serial"]["port"], baud=cfg["serial"]["baud"],
        addr=cfg["serial"]["slave_addr"], timeout=cfg["serial"]["timeout"],
    ) as m:
        _setup(m)
        try:
            for tid in requested:
                fn = TEST_FUNCS.get(tid)
                if fn is None:
                    print(f"  (skipping unknown test {tid})")
                    continue
                fn(m, run_dir, iters=args.iters)
        finally:
            m.enable(False)

    print(f"\nDone. Artifacts in {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Hardware dry run**

Run: `python benchmarks/02_precision.py --tests P1 --iters 10`
Expected: motor moves around, prints σ and peak, writes CSV + PNG.

- [ ] **Step 3: Commit**

```bash
git add benchmarks/02_precision.py
git commit -m "feat(benchmarks): P1 repeatability test"
```

---

## Task 23: Benchmark P3 — error vs speed

**Files:**
- Modify: `benchmarks/02_precision.py`

- [ ] **Step 1: Add `run_p3`**

Append to `benchmarks/02_precision.py` (before `TEST_FUNCS`):
```python
def run_p3(m: MKSServo42D, run_dir: Path, iters: int = 20) -> None:
    """P3: error vs speed — final residual after a 1-turn move at varying RPM."""
    banner(f"P3: error vs speed (iters per RPM = {iters})")
    rpms = [50, 100, 300, 600, 1000, 1500, 2000, 3000]
    csv_path = run_dir / "p3_error_vs_speed.csv"
    rows = []

    # Always start from a known origin
    m.move_absolute_axis(0, rpm=300, acc=10)
    m.wait_until_idle(timeout=15.0)

    for rpm in rpms:
        for i in range(iters):
            origin = m.read_encoder_addition()
            target = origin + degrees_to_encoder_counts(360.0)
            acc = 10 if rpm <= 800 else 50  # gentler for high speed
            m.move_absolute_axis(target, rpm=rpm, acc=acc)
            m.wait_until_idle(timeout=20.0)
            time.sleep(0.05)
            measured = m.read_encoder_addition()
            residual_counts = measured - target
            residual_deg = encoder_counts_to_degrees(residual_counts)
            rows.append({"rpm": rpm, "iter": i, "residual_deg": residual_deg})
        # progress
        last = [r["residual_deg"] for r in rows[-iters:]]
        rms = float(np.sqrt(np.mean(np.square(last))))
        peak = float(np.max(np.abs(last)))
        print(f"  rpm={rpm:>4}  RMS={rms:.4f}°  peak={peak:.4f}°")

    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rpm", "iter", "residual_deg"])
        w.writeheader()
        w.writerows(rows)

    # Aggregate plot
    by_rpm = {}
    for r in rows:
        by_rpm.setdefault(r["rpm"], []).append(r["residual_deg"])
    rpms_sorted = sorted(by_rpm.keys())
    rms_arr = [float(np.sqrt(np.mean(np.square(by_rpm[rp])))) for rp in rpms_sorted]
    peak_arr = [float(np.max(np.abs(by_rpm[rp]))) for rp in rpms_sorted]

    fig, ax = plt.subplots()
    ax.plot(rpms_sorted, rms_arr, marker="o", label="RMS")
    ax.plot(rpms_sorted, peak_arr, marker="s", label="peak")
    ax.set_xlabel("RPM")
    ax.set_ylabel("residual [deg]")
    ax.set_title("P3: position error vs commanded RPM")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(run_dir / "plots" / "p3_error_vs_speed.png", dpi=120)
    plt.close(fig)
    print(f"  → {csv_path.name} + p3_error_vs_speed.png")
```

Update `TEST_FUNCS`:
```python
TEST_FUNCS = {"P1": run_p1, "P3": run_p3}
```

- [ ] **Step 2: Hardware run**

Run: `python benchmarks/02_precision.py --tests P3 --iters 5`
Expected: ~8 RPM levels × 5 moves; final printout has RMS/peak per RPM.

- [ ] **Step 3: Commit**

```bash
git add benchmarks/02_precision.py
git commit -m "feat(benchmarks): P3 error vs speed test"
```

---

## Task 24: Benchmark P5 — follow error during motion

**Files:**
- Modify: `benchmarks/02_precision.py`

- [ ] **Step 1: Add `run_p5`**

Append to `benchmarks/02_precision.py` (before `TEST_FUNCS`):
```python
def run_p5(m: MKSServo42D, run_dir: Path, iters: int = 1) -> None:
    """P5: follow error — poll cmd 0x39 during a slow 1-turn move."""
    banner("P5: follow error (1 turn @ 60 RPM)")
    csv_path = run_dir / "p5_follow_error.csv"
    rows = []

    origin = m.read_encoder_addition()
    target = origin + degrees_to_encoder_counts(360.0)
    m.move_absolute_axis(target, rpm=60, acc=2)
    t0 = time.monotonic()
    deadline = t0 + 15.0  # safety upper bound
    while True:
        err_units = m.read_angle_error()
        err_deg = err_units * 360.0 / 51200
        meas_deg = encoder_counts_to_degrees(m.read_encoder_addition() - origin)
        rows.append({"t_ms": int((time.monotonic() - t0) * 1000),
                     "measured_deg": meas_deg,
                     "follow_err_deg": err_deg})
        if abs(meas_deg - 360.0) < 0.05 or time.monotonic() > deadline:
            break
        time.sleep(0.02)

    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["t_ms", "measured_deg", "follow_err_deg"])
        w.writeheader()
        w.writerows(rows)

    fig, ax = plt.subplots()
    ts = [r["t_ms"] for r in rows]
    errs = [r["follow_err_deg"] for r in rows]
    ax.plot(ts, errs)
    ax.set_xlabel("time [ms]")
    ax.set_ylabel("follow error [deg]")
    ax.set_title("P5: follow error during 1-turn @ 60 RPM, acc=2")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(run_dir / "plots" / "p5_follow_error.png", dpi=120)
    plt.close(fig)
    print(f"  samples={len(rows)} → {csv_path.name} + p5_follow_error.png")
```

Update `TEST_FUNCS`:
```python
TEST_FUNCS = {"P1": run_p1, "P3": run_p3, "P5": run_p5}
```

- [ ] **Step 2: Hardware run**

Run: `python benchmarks/02_precision.py --tests P5`
Expected: ~150-300 samples logged, plot shows transient follow error then steady ~0.

- [ ] **Step 3: Commit**

```bash
git add benchmarks/02_precision.py
git commit -m "feat(benchmarks): P5 follow error test"
```

---

## Task 25: Benchmark V1 — visual calibration verification

**Files:**
- Modify: `benchmarks/02_precision.py`

- [ ] **Step 1: Add `run_v1`**

Append to `benchmarks/02_precision.py` (before `TEST_FUNCS`):
```python
def run_v1(m: MKSServo42D, run_dir: Path, iters: int = 1) -> None:
    """V1: visual calibration check — command 10 turns, count visually."""
    from benchmarks._common import confirm
    banner("V1: visual calibration check (10 turns)")
    confirm("Mark the shaft position (e.g. tape arrow). Then press ENTER to start.")
    origin = m.read_encoder_addition()
    target = origin + 10 * 0x4000
    m.move_absolute_axis(target, rpm=180, acc=20)
    m.wait_until_idle(timeout=30.0)
    measured_counts = m.read_encoder_addition() - origin
    measured_turns = measured_counts / 0x4000
    print(f"  encoder reports {measured_turns:.4f} turns")
    confirm("Visually count the turns the pointer made. Did it match 10?")
    (run_dir / "v1_visual_check.txt").write_text(
        f"Commanded: 10 turns\nEncoder reports: {measured_turns:.6f} turns\n"
        "Visual: confirmed by user (manual)\n"
    )
```

Update `TEST_FUNCS`:
```python
TEST_FUNCS = {"P1": run_p1, "P3": run_p3, "P5": run_p5, "V1": run_v1}
```

- [ ] **Step 2: Update CLI default**

Edit the argparse default in `main()`:
```python
parser.add_argument("--tests", default="P1,P3,P5,V1", help="Comma-separated test ids")
```

- [ ] **Step 3: Hardware run**

Run: `python benchmarks/02_precision.py --tests V1`
Expected: prompts to mark shaft, runs 10 turns, asks to confirm visually.

- [ ] **Step 4: Commit**

```bash
git add benchmarks/02_precision.py
git commit -m "feat(benchmarks): V1 visual calibration check + default-all-tests"
```

---

## Task 26: Benchmark `03_speed.py` — S1 max RPM per mode

**Files:**
- Create: `benchmarks/03_speed.py`

- [ ] **Step 1: Implement S1**

Create `benchmarks/03_speed.py`:
```python
"""03_speed: speed benchmarks (S1, S2, S3).

Usage: python benchmarks/03_speed.py [--tests S1,S2,S3]
Hardware required.
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from mks_servo import MKSServo42D
from mks_servo.constants import Direction, WorkMode
from mks_servo.driver import degrees_to_encoder_counts, encoder_counts_to_degrees
from benchmarks._common import banner, load_config, make_run_dir


MODES = {
    "SR_OPEN": (WorkMode.SR_OPEN, 400),
    "SR_CLOSE": (WorkMode.SR_CLOSE, 1500),
    "SR_vFOC": (WorkMode.SR_vFOC, 3000),
}


def run_s1(m: MKSServo42D, run_dir: Path) -> None:
    banner("S1: max sustainable RPM per mode")
    csv_path = run_dir / "s1_max_rpm_by_mode.csv"
    rows = []
    for mode_name, (mode, max_rated) in MODES.items():
        m.enable(False)
        m.set_work_mode(mode)
        m.set_subdivision(16)
        m.enable(True)
        # Sweep up to 110% of rated, in steps
        for cmd_rpm in np.arange(50, int(max_rated * 1.1), 100, dtype=int).tolist() + [max_rated]:
            m.move_speed(rpm=int(cmd_rpm), acc=10, direction=Direction.CW)
            time.sleep(2.5)  # let it settle to full speed
            measured = m.read_speed_rpm()
            rows.append({"mode": mode_name, "cmd_rpm": int(cmd_rpm), "measured_rpm": measured})
            print(f"  {mode_name:>8s}  cmd={cmd_rpm:>4d}  meas={measured:>5d}")
        m.move_speed(rpm=0, acc=10, direction=Direction.CW)
        time.sleep(1.0)

    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["mode", "cmd_rpm", "measured_rpm"])
        w.writeheader()
        w.writerows(rows)

    fig, ax = plt.subplots()
    for mode_name in MODES:
        sub = [r for r in rows if r["mode"] == mode_name]
        ax.plot([r["cmd_rpm"] for r in sub],
                [abs(r["measured_rpm"]) for r in sub], marker="o", label=mode_name)
    lim = max(r["cmd_rpm"] for r in rows)
    ax.plot([0, lim], [0, lim], "k--", alpha=0.3, label="ideal")
    ax.set_xlabel("commanded RPM")
    ax.set_ylabel("measured RPM (|signed|)")
    ax.set_title("S1: max sustainable RPM per mode")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(run_dir / "plots" / "s1_max_rpm_by_mode.png", dpi=120)
    plt.close(fig)


TEST_FUNCS = {"S1": run_s1}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests", default="S1,S2,S3")
    args = parser.parse_args()

    cfg = load_config()
    run_dir = make_run_dir("speed")
    print(f"Output dir: {run_dir}")

    with MKSServo42D(
        port=cfg["serial"]["port"], baud=cfg["serial"]["baud"],
        addr=cfg["serial"]["slave_addr"], timeout=cfg["serial"]["timeout"],
    ) as m:
        try:
            for tid in [t.strip().upper() for t in args.tests.split(",")]:
                fn = TEST_FUNCS.get(tid)
                if fn:
                    fn(m, run_dir)
                else:
                    print(f"  (skipping {tid})")
        finally:
            try:
                m.move_speed(rpm=0, acc=10, direction=Direction.CW)
                time.sleep(0.5)
            finally:
                m.enable(False)

    print(f"\nDone. Artifacts in {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Hardware run**

Run: `python benchmarks/03_speed.py --tests S1`
Expected: each mode swept; plot shows where measured saturates.

- [ ] **Step 3: Commit**

```bash
git add benchmarks/03_speed.py
git commit -m "feat(benchmarks): S1 max RPM per mode"
```

---

## Task 27: Benchmark S2 — acceleration curve

**Files:**
- Modify: `benchmarks/03_speed.py`

- [ ] **Step 1: Add `run_s2`**

Append to `benchmarks/03_speed.py` before `TEST_FUNCS`:
```python
def run_s2(m: MKSServo42D, run_dir: Path) -> None:
    """S2: acceleration curve — sample read_speed_rpm() while ramping to 2000 RPM."""
    banner("S2: acceleration curve (target 2000 RPM)")
    m.enable(False)
    m.set_work_mode(WorkMode.SR_vFOC)
    m.enable(True)
    target_rpm = 2000
    accs = [1, 50, 100, 200, 255]
    csv_path = run_dir / "s2_accel.csv"
    rows = []

    for acc in accs:
        # ensure stopped
        m.move_speed(rpm=0, acc=255, direction=Direction.CW)
        time.sleep(1.0)
        m.move_speed(rpm=target_rpm, acc=acc, direction=Direction.CW)
        t0 = time.monotonic()
        while True:
            v = abs(m.read_speed_rpm())
            t = (time.monotonic() - t0) * 1000
            rows.append({"acc": acc, "t_ms": int(t), "rpm": v})
            if v >= target_rpm or t > 8000:
                break
            time.sleep(0.01)
        m.move_speed(rpm=0, acc=255, direction=Direction.CW)
        time.sleep(1.5)

    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["acc", "t_ms", "rpm"])
        w.writeheader()
        w.writerows(rows)

    fig, ax = plt.subplots()
    for acc in accs:
        sub = [r for r in rows if r["acc"] == acc]
        ax.plot([r["t_ms"] for r in sub], [r["rpm"] for r in sub], label=f"acc={acc}")
        # theoretical: dt per +1 RPM = (256-acc)*50e-6 s -> per RPM = (256-acc)*0.05 ms
        # so v(t [ms]) = t / ((256-acc)*0.05)
        if acc < 256:
            t_max = max(r["t_ms"] for r in sub)
            ts = np.linspace(0, t_max, 50)
            vs = np.minimum(target_rpm, ts / ((256 - acc) * 0.05))
            ax.plot(ts, vs, "--", alpha=0.4)
    ax.set_xlabel("time [ms]")
    ax.set_ylabel("measured RPM")
    ax.set_title("S2: ramp to 2000 RPM (solid=measured, dashed=theoretical)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(run_dir / "plots" / "s2_accel.png", dpi=120)
    plt.close(fig)
```

Update `TEST_FUNCS`:
```python
TEST_FUNCS = {"S1": run_s1, "S2": run_s2}
```

- [ ] **Step 2: Hardware run**

Run: `python benchmarks/03_speed.py --tests S2`
Expected: 5 ramps recorded; plot compares measured vs theoretical.

- [ ] **Step 3: Commit**

```bash
git add benchmarks/03_speed.py
git commit -m "feat(benchmarks): S2 acceleration curve vs theoretical"
```

---

## Task 28: Benchmark S3 — stall threshold

**Files:**
- Modify: `benchmarks/03_speed.py`

- [ ] **Step 1: Add `run_s3`**

Append to `benchmarks/03_speed.py` before `TEST_FUNCS`:
```python
def run_s3(m: MKSServo42D, run_dir: Path) -> None:
    """S3: stall threshold — 10-turn move at increasing RPM in SR_CLOSE mode."""
    banner("S3: stall threshold")
    m.enable(False)
    m.set_work_mode(WorkMode.SR_CLOSE)
    m.set_subdivision(16)
    m.enable(True)
    rpms = [500, 1000, 1300, 1500, 1700, 2000, 2500]
    csv_path = run_dir / "s3_stall.csv"
    rows = []

    m.move_absolute_axis(0, rpm=300, acc=20)
    m.wait_until_idle(timeout=15.0)

    for rpm in rpms:
        try:
            origin = m.read_encoder_addition()
            target = origin + 10 * 0x4000
            m.move_absolute_axis(target, rpm=rpm, acc=50)
            m.wait_until_idle(timeout=30.0)
            time.sleep(0.3)
            measured = m.read_encoder_addition()
            residual_counts = measured - target
            residual_deg = encoder_counts_to_degrees(residual_counts)
            angle_err_units = m.read_angle_error()
            print(f"  rpm={rpm:>4}  residual={residual_deg:+.4f}°  angle_err={angle_err_units}")
            rows.append({"rpm": rpm, "residual_deg": residual_deg,
                         "angle_err_units": angle_err_units, "ok": abs(residual_deg) < 1.0})
        except Exception as e:
            print(f"  rpm={rpm}  FAILED: {e}")
            rows.append({"rpm": rpm, "residual_deg": float("nan"),
                         "angle_err_units": -1, "ok": False})
            try:
                m.release_protection()
                m.move_absolute_axis(0, rpm=300, acc=20)
                m.wait_until_idle(timeout=15.0)
            except Exception:
                pass

    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rpm", "residual_deg", "angle_err_units", "ok"])
        w.writeheader()
        w.writerows(rows)

    fig, ax = plt.subplots()
    ax.plot([r["rpm"] for r in rows], [abs(r["residual_deg"]) for r in rows], marker="o")
    ax.axhline(1.0, color="r", linestyle="--", alpha=0.5, label="1° threshold")
    ax.set_xlabel("RPM")
    ax.set_ylabel("|residual after 10 turns| [deg]")
    ax.set_title("S3: stall threshold (SR_CLOSE)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(run_dir / "plots" / "s3_stall.png", dpi=120)
    plt.close(fig)
```

Update `TEST_FUNCS`:
```python
TEST_FUNCS = {"S1": run_s1, "S2": run_s2, "S3": run_s3}
```

- [ ] **Step 2: Hardware run**

Run: `python benchmarks/03_speed.py --tests S3`
Expected: each RPM tested; identifies the first RPM where residual exceeds 1°.

- [ ] **Step 3: Commit**

```bash
git add benchmarks/03_speed.py
git commit -m "feat(benchmarks): S3 stall threshold (SR_CLOSE)"
```

---

## Task 29: Benchmark `04_persistence.py` — C1 + C2 + C3

**Files:**
- Create: `benchmarks/04_persistence.py`

- [ ] **Step 1: Implement all three tests**

Create `benchmarks/04_persistence.py`:
```python
"""04_persistence: configuration persistence across power-cycles (C1, C2, C3).

Usage: python benchmarks/04_persistence.py [--tests C1,C2,C3]
Hardware required. ⚠ asks user to physically power-cycle the 12V (USB stays connected).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from mks_servo import MKSServo42D
from mks_servo.constants import WorkMode
from mks_servo.driver import degrees_to_encoder_counts
from benchmarks._common import banner, confirm, load_config, make_run_dir


def _open(cfg, addr_override: int | None = None) -> MKSServo42D:
    return MKSServo42D(
        port=cfg["serial"]["port"], baud=cfg["serial"]["baud"],
        addr=addr_override if addr_override else cfg["serial"]["slave_addr"],
        timeout=cfg["serial"]["timeout"],
    )


def run_c1(cfg, run_dir: Path) -> None:
    banner("C1: full config diff across power-cycle")
    with _open(cfg) as m:
        cfg_pre = m.read_all_config()
        (run_dir / "c1_pre.json").write_text(json.dumps(
            {**{k: v for k, v in cfg_pre.items() if k != "raw"},
             "raw_hex": cfg_pre["raw"].hex()}, indent=2))
    confirm("Disconnect 12V from the motor, wait 3 seconds, reconnect.")
    time.sleep(0.5)
    with _open(cfg) as m:
        cfg_post = m.read_all_config()
        (run_dir / "c1_post.json").write_text(json.dumps(
            {**{k: v for k, v in cfg_post.items() if k != "raw"},
             "raw_hex": cfg_post["raw"].hex()}, indent=2))
    same = cfg_pre["raw"] == cfg_post["raw"]
    diff_path = run_dir / "c1_diff.txt"
    if same:
        diff_path.write_text("PASS — pre and post raw match.\n")
        print("  PASS")
    else:
        lines = ["FAIL — bytes differ:"]
        for i, (a, b) in enumerate(zip(cfg_pre["raw"], cfg_post["raw"])):
            if a != b:
                lines.append(f"  byte {i}: pre=0x{a:02X}  post=0x{b:02X}")
        diff_path.write_text("\n".join(lines) + "\n")
        print("  FAIL — see c1_diff.txt")


def run_c2(cfg, run_dir: Path) -> None:
    banner("C2: calibration persists")
    confirm("Mark the shaft. Then press ENTER to do 10 turns BEFORE power-cycle.")
    with _open(cfg) as m:
        m.set_work_mode(WorkMode.SR_vFOC)
        m.enable(True)
        origin = m.read_encoder_addition()
        m.move_absolute_axis(origin + 10 * 0x4000, rpm=180, acc=20)
        m.wait_until_idle(timeout=30.0)
        end_pre = m.read_encoder_addition()
        turns_pre = (end_pre - origin) / 0x4000
        m.enable(False)
    print(f"  encoder reports {turns_pre:.4f} turns BEFORE power-cycle")
    confirm("Disconnect 12V, wait 3 s, reconnect. Pointer should be back near start mark.")
    time.sleep(0.5)
    with _open(cfg) as m:
        m.set_work_mode(WorkMode.SR_vFOC)
        m.enable(True)
        origin = m.read_encoder_addition()
        m.move_absolute_axis(origin + 10 * 0x4000, rpm=180, acc=20)
        m.wait_until_idle(timeout=30.0)
        end_post = m.read_encoder_addition()
        turns_post = (end_post - origin) / 0x4000
        m.enable(False)
    print(f"  encoder reports {turns_post:.4f} turns AFTER power-cycle (no recalibration)")
    (run_dir / "c2_calibration.txt").write_text(
        f"Pre  : {turns_pre:.6f} turns\nPost : {turns_post:.6f} turns\n"
        "Visual: confirmed by user (manual)\n"
    )


def run_c3(cfg, run_dir: Path) -> None:
    banner("C3: custom params survive power-cycle")
    target_current = 2200
    target_subdiv = 64
    target_addr = 7
    original_addr = cfg["serial"]["slave_addr"]

    with _open(cfg) as m:
        m.set_work_current_ma(target_current)
        m.set_subdivision(target_subdiv)
        # Set address LAST — after this the motor responds at the new address
        from mks_servo.constants import OpCode
        m._txn(OpCode.SET_SLAVE_ADDR, bytes([target_addr]), expect_payload_len=1)
    confirm("Disconnect 12V, wait 3 s, reconnect.")
    time.sleep(0.5)

    try:
        with _open(cfg, addr_override=target_addr) as m:
            cfg_post = m.read_all_config()
        ok = (cfg_post["current_ma"] == target_current
              and cfg_post["subdivision"] == target_subdiv
              and cfg_post["slave_addr"] == target_addr)
        line = (f"current={cfg_post['current_ma']} subdiv={cfg_post['subdivision']} "
                f"addr={cfg_post['slave_addr']} -> {'PASS' if ok else 'FAIL'}")
        print(f"  {line}")
        (run_dir / "c3_custom_params.txt").write_text(line + "\n")
    finally:
        # CRITICAL: restore address to the original
        banner("C3 cleanup: restoring slave address")
        try:
            with _open(cfg, addr_override=target_addr) as m:
                from mks_servo.constants import OpCode
                m._txn(OpCode.SET_SLAVE_ADDR, bytes([original_addr]), expect_payload_len=1)
            print(f"  restored slave addr -> {original_addr}")
        except Exception as e:
            print(f"  ⚠ failed to restore addr: {e}\n  Manually set UartAddr={original_addr} from menu.")


TEST_FUNCS = {"C1": run_c1, "C2": run_c2, "C3": run_c3}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests", default="C1,C2,C3")
    args = parser.parse_args()
    cfg = load_config()
    run_dir = make_run_dir("persistence")
    print(f"Output dir: {run_dir}")
    for tid in [t.strip().upper() for t in args.tests.split(",")]:
        fn = TEST_FUNCS.get(tid)
        if fn:
            fn(cfg, run_dir)
        else:
            print(f"  (skipping {tid})")
    print(f"\nDone. Artifacts in {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Hardware run, one test at a time**

Run: `python benchmarks/04_persistence.py --tests C1`
Expected: prompt to power-cycle; produces `c1_pre.json`, `c1_post.json`, `c1_diff.txt` ("PASS").

Run: `python benchmarks/04_persistence.py --tests C2`
Expected: prompt to mark shaft, motor turns 10 times pre, power-cycle, motor turns 10 times post; visual confirms.

Run: `python benchmarks/04_persistence.py --tests C3`
Expected: address changes to 7, power-cycle, verifies, then restores to 1.

- [ ] **Step 3: Commit**

```bash
git add benchmarks/04_persistence.py
git commit -m "feat(benchmarks): C1/C2/C3 persistence tests"
```

---

## Task 30: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

Create `README.md`:
````markdown
# Stepper Motor Test (MKS SERVO42D RS485 + NEMA17)

Characterization library + benchmark suite for a closed-loop NEMA17 stepper motor driven by an MKS SERVO42D RS485 driver.

## Hardware

- NEMA17 wired to MKS SERVO42D (motor phase resistance < 10 Ω)
- Power supply: 12–24 V on `V+`/`GND` of the driver
- USB↔RS485 adapter (e.g. CH340/FT232 + MAX485) on `A`/`B`
- (For visual tests) a pointer or marked feature on the shaft

## Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

Edit `config.toml` to match your serial port and baud:

```toml
[serial]
port = "/dev/ttyUSB0"
baud = 38400
slave_addr = 1
timeout = 0.5
```

## Tests (no hardware)

```bash
pytest                # unit tests for protocol + driver (mocked serial)
```

## Benchmarks (require motor connected)

Run in this order. Each writes a fresh directory under `results/`.

```bash
python benchmarks/01_smoke.py [--calibrate]   # ping + dump config + optional calibrate
python benchmarks/02_precision.py             # P1, P3, P5, V1
python benchmarks/03_speed.py                 # S1, S2, S3
python benchmarks/04_persistence.py           # C1, C2, C3 (requires manual power-cycles)
```

Run a subset with `--tests`, e.g. `python benchmarks/02_precision.py --tests P1,P3`.

## Output

`results/<bench>_<UTC-timestamp>/` contains CSVs, JSONs, and PNG plots.

## Library use

```python
from mks_servo import MKSServo42D, WorkMode

with MKSServo42D(port="/dev/ttyUSB0", baud=38400, addr=1) as m:
    m.set_work_mode(WorkMode.SR_vFOC)
    m.enable(True)
    m.move_relative_axis(0x4000, rpm=300, acc=10)
    m.wait_until_idle()
    print(m.read_angle_degrees())
```

## Design + plan

- Spec: `docs/superpowers/specs/2026-05-09-stepper-motor-test-design.md`
- Plan: `docs/superpowers/plans/2026-05-09-stepper-motor-test.md`
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and usage"
```

---

## Self-review checklist

After all tasks done, verify:

- [ ] `pytest` (no hardware) passes — should be ~40+ unit tests
- [ ] `python benchmarks/01_smoke.py` works on connected hardware
- [ ] All four benchmark scripts have an entry per planned MVP test (P1, P3, P5, V1, S1, S2, S3, C1, C2, C3)
- [ ] No TODO/TBD strings in code or docs
- [ ] Method signatures used in benchmarks (e.g. `move_absolute_axis(counts, rpm, acc)`) match what's defined on `MKSServo42D`
- [ ] `config.toml` `slave_addr` matches the address embedded in the driver (default 1)
- [ ] After running C3, the slave address is restored to 1 (the script does this in `finally`)
- [ ] After running C4 (if you ever run it — it's NOT in the MVP), you re-run `01_smoke.py --calibrate`
