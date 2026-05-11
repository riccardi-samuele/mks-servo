# Multi-motor on one RS485 bus

`MotorBus` coordinates N motors that share a single physical RS485
transport. Each motor needs a unique `slave_addr` (1..247).

## Setup

1. Each driver must have a unique address. Set them either:
   - via the OLED menu on the SERVO42D, or
   - programmatically (one driver at a time, alone on the bus):
     `motor.raw.set_slave_addr(<new_addr>)`.

2. Create a profile per motor (each pinned to its `slave_addr`).

3. Use `MotorBus`:

   ```python
   from mks_servo import MotorBus
   with MotorBus("/dev/ttyUSB0", baud=38400) as bus:
       wrist = bus.add("./profiles/wrist.yaml")
       elbow = bus.add("./profiles/elbow.yaml")
       wrist.write(45)
       elbow.write(90)
   ```

## Discovery

```bash
mks-servo bus discover --port /dev/ttyUSB0 --range 1-16
```

For each responsive driver, the CLI prints: address, model, mode, current,
subdivision.

To also generate profile YAMLs:

```bash
mks-servo bus discover --port /dev/ttyUSB0 --range 1-16 --create-profiles
```

Files are written to `./profiles/motor_<addr>.yaml` (or `--out <dir>`).
Refuses to overwrite existing files unless `--force` is passed.

## Locking and concurrency

The bus uses a `threading.Lock` to serialise transactions, so even if
multiple threads call `wrist.write(...)` and `elbow.write(...)` concurrently,
the actual serial I/O is sequential (RS485 is half-duplex). For a
single-threaded program this is transparent overhead; for multi-threaded
use the lock is correctness-critical.

## Programmatic discovery

Without the CLI:

```python
from mks_servo import MotorBus

with MotorBus("/dev/ttyUSB0") as bus:
    entries = bus.scan(range(1, 17))
    for e in entries:
        print(f"addr={e.addr}: {e.model}")
```

`bus.scan()` returns `list[BusEntry]`. Each entry has `.addr`, `.model`,
and `.config` (the raw `read_all_config()` dict). With
`create_profiles=True` it also has `.profile` (the saved Profile object).

## Caveats

- All motors on the bus share the same baud rate. Mixed baud rates require
  separate `MotorBus` instances on different USB-RS485 dongles.
- `MotorBus.scan()` uses a 1s per-address timeout by default; a 16-address
  scan therefore takes up to ~16s if no drivers respond. Adjust via
  `bus.scan(timeout=0.5)` for impatient setups.
- Motor lifecycle: `bus.add(profile)` calls `Motor.attach()` automatically.
  `bus.close()` (via `__exit__`) detaches all motors before closing the
  transport. You can also call `bus.remove(motor)` to detach a single
  motor while keeping the bus open.
- The shared transport's lock protects each `transact()` call. It does NOT
  protect against API-level interleaving. If you need a "read-then-write"
  to be atomic across threads, hold your own lock around the pair.
