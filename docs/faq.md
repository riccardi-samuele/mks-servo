# FAQ — firmware quirks and gotchas

Pragmatic notes from real HIL bring-up on a SERVO42D V1.0.6 + NEMA17 + 12&nbsp;V rig.

## `wait_until_idle()` never returns after a move

**Symptom.** A closed-loop move finishes physically, but the status byte
returned by cmd `0xF1` latches in `SPEED_DOWN` forever.

**Cause.** Firmware V1.0.6 quirk: the driver doesn't clear the
`SPEED_DOWN` state after a closed-loop move even when `speed_rpm` is zero.

**What v1.0 does.** `RawDriver.wait_until_idle` also treats *N consecutive
reads with `speed_rpm == 0`* as idle, with two guards: it requires either
observed motion or a minimum warmup time before counting zero-streaks (so
a no-op move can't return prematurely), and it tolerates one `CommTimeout`
per iteration (truncated frames during motion are common).

## `attach()` raises `CommTimeout` on `set_work_mode` / `set_subdivision` / `set_work_current_ma`

**Symptom.** Reopening the serial port shortly after a previous session
makes the first config write in `attach()` time out.

**Cause.** If the motor is still coasting down from the previous session
when the port is reopened, the firmware sometimes drops the reply to the
first command issued on the fresh connection.

**What v1.0 does.** `Motor._apply_profile_config` retries each
profile-config write once after a 0.3&nbsp;s settle if it sees a
`CommTimeout`. Visible only to debug logging — the call still raises if
both attempts fail.

## `set_origin(soft=False)` occasionally raises `CommTimeout`

**Symptom.** A `set_origin()` call immediately after a move times out.

**Cause.** Cmd `0x92` is more sensitive than most: the driver can stall
its reply if there is residual motion or torque ripple.

**What v1.0 does.** `Motor.set_origin(soft=False)` adds a 0.2&nbsp;s
settle and one retry on `CommTimeout`.

## `OSError(EIO=5)` slipping past `except CommTimeout`

**Symptom.** During a long-running soak the USB-RS485 adapter physically
drops off the bus. `pyserial` raises a bare `OSError`, application code
that only handles `CommTimeout` crashes.

**What v1.0 does.** `transport.transact()` wraps `OSError` *and*
`serial.SerialException` from `ser.read()` / `ser.write()` /
`ser.reset_input_buffer()` / `ser.flush()` and re-raises as
`CommTimeout`, with the original on `__cause__`. A single
`except CommTimeout` is enough to catch every "did not complete" path,
which is what callers want.

## `CharacterizationSuite.run_s2_acceleration` returns `time_to_target_ms=[None, …]`

**Symptom.** Useful S2 acceleration result but the time-to-target column
is all `None` on a 12&nbsp;V rig.

**Cause.** Default `samples_per_acc=50 × 0.01 s ≈ 0.5 s` sampling window
against a 2000&nbsp;RPM target is too short for a 12&nbsp;V supply, which
tops out around 1350&nbsp;RPM here — the motor never reaches 95% of
target inside the window.

**Workaround.** Either run with a lower target RPM, or supply a longer
sampling window via the `S2Params`. `max_observed_rpm` is still
populated, so the result is well-formed. Revisiting S2 defaults for low
supply voltages is a v1.x task.

## Calibration (`motor.calibrate()`) doesn't fire

**Symptom.** Calibration succeeds in driver-side logging but the motor
doesn't physically move.

**Cause.** Calibration needs explicit settle/poll cycles between commands;
the firmware silently buffers a calibrate-then-status read otherwise.

**What v1.0 does.** `Motor.calibrate()` runs the documented sequence with
the appropriate delays. If you hit it from `motor.raw` directly, mirror
the per-step settle pauses you'll find in the `Motor` implementation.

## I want to use this on Windows / macOS / a different driver

**Windows / macOS.** Supported (smoke-tested in CI on Python 3.13).
Replace `/dev/ttyUSB0` with the appropriate `COM*` (Windows) or
`/dev/tty.*` (macOS) device path.

**Different driver.** `DRIVER_REGISTRY` + `make_raw_driver(model, ...)`
let you plug in a per-model `RawDriver`. Only `SERVO42D` is shipped in
1.0; a real `SERVO57D` driver is a 1.x task (the registry hook is the
only thing reserved for it today).
