# Contributing to mks-servo

Thanks for considering a contribution! This guide covers the practical bits.

## TL;DR

```bash
git clone <fork-url> && cd stepper_motor_test
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,bench]"
pytest -q                     # 311 mocked tests, no hardware
pytest -m hil                 # HIL tests — requires the rig (see below)
```

## What the project is

A Python library wrapping the MKS SERVO42D RS485 closed-loop stepper driver
firmware (V1.0.6). Progressive-disclosure API:

| Level | Surface | When to use |
|-------|---------|-------------|
| 0     | `Motor.attach/detach/write/read/error/is_moving/emergency_stop` | "Arduino Servo, but more powerful" |
| 1     | `motor.work_current_ma`, `set_origin`, `calibrate`, `move_relative`, properties, … | day-to-day robotics code |
| 2     | `motor.advanced.*`, `motor.diagnostics.*` | flash-rewriting + health checks |
| 3     | `motor.raw.*` — the 1:1 opcode wrapper | protocol-level control |

See `docs/superpowers/specs/2026-05-09-mks-servo-vision.md` for the design
philosophy and the level boundaries.

## Workflow

We follow **TDD**: write a failing test first, make it pass, refactor. The
repo organises tests by surface:

- `tests/test_motor_*.py` — Level 0/1 (use the `mock_raw` + `base_profile`
  fixtures from `tests/conftest.py`).
- `tests/test_raw_*.py` — Level 3 (patch `mks_servo.raw.serial.Serial`).
- `tests/test_bus_*.py`, `tests/test_transport.py` — Multi-motor.
- `tests/test_characterize_*.py` — Programmatic characterization.
- `tests/test_cli_*.py` — `mks-servo` CLI (`click.testing.CliRunner`).
- `tests/hil/*.py` — Hardware-in-the-loop, marked `@pytest.mark.hil`,
  **deselected by default**.

Branch off `master`. Keep commits focused and atomic. Use Conventional
Commits prefixes (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).

## Running the test suite

| Command | What |
|---------|------|
| `pytest -q` | All mocked tests. ~5 s on a laptop. Must pass before any PR. |
| `pytest -m hil` | HIL tests. Requires the rig (see below). |
| `pytest tests/test_motor_lifecycle.py -v` | One file |
| `pytest -k attach_retries` | One test by keyword |

## Hardware-in-the-loop (HIL) testing

HIL tests are how we caught the 6 bugs that v0.1.0's mocked-only suite
missed. If you're touching motion, transport, or bus code, you should run
them.

**Rig:**
- NEMA17 (or compatible) stepper, **mechanically unloaded** for the
  calibrate test (`tests/hil/test_calibrate.py` spins the motor at high
  current — anything attached can be damaged).
- MKS SERVO42D driver with firmware V1.0.6.
- 12 V power supply.
- USB-RS485 adapter at `/dev/ttyUSB0` (Linux). Set the slave address on the
  driver to 1 (or edit `config.toml`).

**Config:**

`config.toml` at the repo root tells the HIL fixtures where the rig is:

```toml
[serial]
port = "/dev/ttyUSB0"
baud = 38400
slave_addr = 1
timeout = 3.0
```

**Run:**

```bash
pytest -m hil                                         # everything
pytest -m hil tests/hil/test_bus_concurrent.py -v     # one file
pytest -m hil --deselect tests/hil/test_calibrate.py  # skip the slow one
```

The two-motor test self-skips unless you set `MKS_HIL_SECOND_ADDR=<addr>`
for a second driver on the same bus.

## Firmware quirks worth knowing

These are baked into `RawDriver.wait_until_idle` and `Motor.attach/set_origin`
so callers don't have to think about them. If your change touches those
methods, keep the workarounds:

- **Status latches in SPEED_DOWN** after a closed-loop move (cmd 0xF1 never
  returns to STOPPED). `wait_until_idle` also accepts `read_speed_rpm() == 0`
  for N consecutive reads.
- **Driver less responsive during motion** — 50 ms polling produces truncated
  frames. Default `poll_interval=0.2 s`, and one `CommTimeout` per iteration
  is tolerated.
- **Calibration needs delays between commands** — see `_CALIB_DELAY_S` in
  `motor.py`.
- **First commands after a fresh connection may drop** if the motor is still
  coasting from a previous session — `Motor.attach()` retries config writes
  once on `CommTimeout`.

## Code style

- Match the surrounding code's idiom — comment density, naming, line length.
- No new dependencies without discussion.
- Type-hint public APIs.
- Keep files focused; if a file is doing two unrelated things, split it.

## Pull requests

1. PR titles use the same Conventional Commits prefixes as commit messages.
2. Tests must pass (`pytest -q`); HIL changes need an HIL log pasted in the
   PR description.
3. Add a `CHANGELOG.md` entry under `## [Unreleased]` for user-visible changes.
4. One logical change per PR. Small PRs get merged faster.

## Releasing

(Maintainers only.) Currently manual: bump `pyproject.toml` `version`, update
`CHANGELOG.md`, `git tag -a vX.Y.Z`, then `python -m build` + `twine upload`.
PyPI publishing is not yet automated (planned for the v1.0 cycle).
