# Characterization

`CharacterizationSuite` runs a curated set of empirical tests and writes the
findings into `profile.characterization`. The same logic that powers
`benchmarks/02_precision.py` and `benchmarks/03_speed.py` is exposed
programmatically via dataclass results.

## Tests

| Test | What it measures | Stored in profile |
|---|---|---|
| **P1** | Repeatability — read-back spread for the same target | `precision.sigma_deg`, `precision.peak_deg` |
| **P3** | RMS positioning error vs. RPM | (logged only) |
| **P5** | Maximum follow error during a sustained sweep | (logged only) |
| **S2** | Acceleration curves to target RPM, max observed RPM | `speed.max_measured_rpm` |

C1/C2/C3 (persistence) are NOT in the suite — they require power-cycle.
S1/S3 (mode-cap RPM) are NOT in the suite — known firmware bug. Use the
existing `benchmarks/03_speed.py` and `benchmarks/04_persistence.py`
scripts to investigate those manually.

## CLI

```bash
mks-servo characterize <profile> [--suite=mvp|full]
                                  [--update-profile] [--save]
                                  [--port /dev/ttyUSB0]
```

`--update-profile` writes the precision sigma/peak and max RPM into the
in-memory profile. `--save` then persists the YAML. `--save` without
`--update-profile` is a no-op (warning printed).

## Programmatic usage

```python
from mks_servo import Motor, CharacterizationSuite

with Motor.from_profile("wrist") as m:
    suite = CharacterizationSuite(m)

    # Run individually:
    p1 = suite.run_p1_precision(iterations=10)
    print(f"sigma={p1.sigma_deg:.3f}°, peak={p1.peak_deg:.3f}°")

    # Or all at once:
    suite.run_mvp()
    suite.update_profile()
    m.profile.save()
```

## Result dataclasses

```python
from mks_servo import SuiteResult, P1Result, P3Result, P5Result, S2Result
```

- `P1Result(target_deg, iterations, samples_deg, mean_deg, sigma_deg, peak_deg)`
- `P3Result(rpm_samples, rms_error_deg)`
- `P5Result(rpm, duration_s, max_follow_err_deg, rms_follow_err_deg)`
- `S2Result(target_rpm, accs, time_to_target_ms, max_observed_rpm)`
- `SuiteResult(p1, p3, p5, s2)` — all optional (None until that test ran)

## Caveats

- Default RPMs in `run_p3_error_vs_rpm` are `[50, 100, 300, 500, 1000]` —
  honest values for the NEMA17 + SERVO42D + 12V setup characterized on
  2026-05-09 (see `docs/reports/2026-05-09-test-report.md`). Adjust for
  your hardware.
- `run_s2_acceleration` uses `motor.raw.move_speed` (Level 3) because
  `Motor` v0.3 does not expose velocity mode at the high level. This is
  intentional — see vision document.
- `update_profile()` does NOT save the YAML; you call `motor.profile.save()`
  yourself. This makes the workflow explicit and allows you to inspect the
  in-memory profile before persisting.
- The suite reads `motor.error()` during P5; if a transient comm error
  occurs mid-sweep, the loop terminates early and you get a partial
  result.
