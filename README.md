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
