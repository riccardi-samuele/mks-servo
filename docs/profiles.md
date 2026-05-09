# Profile reference

A profile is a YAML file describing one motor: model, transport, operating
config, software limits, mechanical info, calibration results.

## Schema (`schema_version: 1`)

The full annotated schema is in the v0.1.0 design spec §3.1. Below is a
condensed reference.

```yaml
schema_version: 1
id: wrist
description: ""
driver:
  model: servo42d           # only servo42d in v0.1.0
  firmware_min: "1.0.6"
  slave_addr: 1
transport:
  port: null                # null → pass via Motor.from_profile(..., port=...)
  baud: 38400
  timeout_s: 3.0
config:
  mode: SR_vFOC             # SR_OPEN | SR_CLOSE | SR_vFOC
  microsteps: 16            # 1..256
  work_current_ma: 1500     # 0..limits.current.max_ma
  hold_current_pct: 50      # 10..90, step 10
  direction: CW             # CW | CCW
limits:
  position:
    min_deg: null           # null = unlimited
    max_deg: null
    on_violation: reject    # reject | clamp | warn
  speed:
    max_rpm_safe: null
    on_violation: clamp
  current:
    max_ma: 3000            # always reject — current cannot be safely clamped
origin:
  set_in_firmware: true
  encoder_offset_counts: 0
mechanical:
  motor_model: ""
  full_steps_per_rev: 200
  gear_ratio: 1.0
characterization:
  last_calibrated: null
  precision: { sigma_deg: null, peak_deg: null }
  speed: { max_measured_rpm: null, voltage_v: null }
```

## Lookup order

`Profile.load(name)` — and `Motor.from_profile(name)` — search:

1. `./profiles/<name>.yaml`         (project)
2. `~/.config/mks-servo/profiles/<name>.yaml`  (user)
3. `<package>/profiles/_templates/<name>.yaml` (built-in templates)

If `name` ends with `.yaml`/`.yml` and points to an existing file, that
specific path is used.

## Creating a profile

### From a built-in template

```bash
mks-servo profile from-template nema17-bipolar-2A --as wrist
```

### From a connected driver (introspection)

```bash
mks-servo profile from-driver --port /dev/ttyUSB0 --addr 1 --as wrist
```

`from-driver` populates `driver`, `transport.baud`, and `config`. Limits,
mechanical info, and characterization data are NOT populated (they're not
knowable from the driver).

## Software limits

Limits are checked by `Motor` *before* any raw command. Three policies:

- `reject` — raise `LimitExceeded`. Default for position. Safest for
  robotics.
- `clamp` — saturate at the limit and proceed. Default for speed. Useful for
  stress tests.
- `warn` — log a warning and proceed unchanged. For debugging.

Current limit (`limits.current.max_ma`) is always `reject` — clamping a
current setpoint would mask an unsafe configuration.

Runtime overrides are in-memory (do NOT mutate the profile):

```python
motor.position_limits = (-45.0, 45.0)   # tighter than profile, in-memory
motor.position_limits = (None, None)    # disable entirely
motor.speed_limit_rpm = 800
```

## Origin (zero point)

Two modes:

- **Firmware** (default, `set_in_firmware: true`): `motor.set_origin()`
  writes via cmd 0x92 — persists in driver flash across power-cycle.
- **Software**: `motor.set_origin(soft=True)` stores `encoder_offset_counts`
  in the profile. Lighter (no flash write) but lost if profile is deleted.

## Saving a modified profile

```python
prof = motor.profile
prof.config.work_current_ma = 1800
prof.save()                # writes back to prof.path
prof.save("/other/path.yaml")  # different target
```

`save()` updates `updated_at` automatically. If the profile was loaded from
a built-in template (`prof.path is None`), pass an explicit path or you'll
get a `ProfileError`.
