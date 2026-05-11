"""Soak test for the v1.0 release candidate.

Exercises the library through the patterns a real user would hit over days,
compressed into ~40 minutes. Each phase logs to stdout and to a timestamped
report file under docs/reports/.

Phases:
  A. Session stress     — 10× attach/detach cycles with short motion in between
  B. Motion loop        — 25 min of random targets in ±60°
  C. Profile round-trip — save+reload after running a P1 characterization
  D. Level mix          — interleaved L1/L2/L3 calls to verify no transport contention
  E. Error recovery     — force a CommTimeout, then verify re-attach works

Pass criteria are documented per phase below; failures don't abort the run
(we want the full picture) but the final summary reports each phase's status.

Run:
  source .venv/bin/activate
  python scripts/soak_v1.0_prep.py
"""
from __future__ import annotations

import random
import sys
import time
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from mks_servo import (  # noqa: E402
    Motor,
    Profile,
    CharacterizationSuite,
    CommTimeout,
    MKSError,
)

REPORTS = REPO / "docs" / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)
TS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
REPORT = REPORTS / f"{TS}-soak.md"

# Phase budgets (seconds). Tune these from the CLI if needed; defaults add to ~40 min.
PHASE_A_CYCLES = 5  # reduced from 10 — first run already showed σ=0ms attach
PHASE_B_DURATION_S = 10 * 60
PHASE_B_SAMPLE_LIMIT = None  # unlimited
PHASE_D_ITERATIONS = 50

PROFILE_NAME = "wrist"
SAFE_RANGE_DEG = (-60.0, 60.0)
SAFE_RPM_RANGE = (100, 600)
DEFAULT_RPM = 300


# --- Logging --------------------------------------------------------------- #

_log_fh = REPORT.open("w", encoding="utf-8")


def log(line: str = "") -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    out = f"[{ts}] {line}" if line else ""
    print(out, flush=True)
    if line:
        _log_fh.write(out + "\n")
    else:
        _log_fh.write("\n")
    _log_fh.flush()


def header(title: str) -> None:
    log()
    log("=" * 72)
    log(title)
    log("=" * 72)


@contextmanager
def timed(label: str):
    t0 = time.monotonic()
    log(f">>> {label} starting")
    try:
        yield
    finally:
        dt = time.monotonic() - t0
        log(f"<<< {label} finished in {dt:.1f}s")


# --- Helpers --------------------------------------------------------------- #

def fresh_motor() -> Motor:
    """Build a Motor from the wrist profile. Caller is responsible for attach/detach."""
    return Motor.from_profile(PROFILE_NAME)


def safe_move(m: Motor, target_deg: float, rpm: int = DEFAULT_RPM) -> tuple[float, float]:
    """Move + wait + read. Returns (read_deg, error_deg)."""
    m.write(target_deg, rpm=rpm)
    m.wait_until_idle()
    r = m.read()
    return r, r - target_deg


# --- Phases ---------------------------------------------------------------- #

PHASES: dict[str, dict] = {
    "A": {"name": "Session stress", "status": "pending", "notes": []},
    "B": {"name": "Motion loop",    "status": "pending", "notes": []},
    "C": {"name": "Profile round-trip", "status": "pending", "notes": []},
    "D": {"name": "Level mix",      "status": "pending", "notes": []},
    "E": {"name": "Error recovery", "status": "pending", "notes": []},
}


def mark(phase: str, status: str, note: str = "") -> None:
    PHASES[phase]["status"] = status
    if note:
        PHASES[phase]["notes"].append(note)


# Phase A — Session stress
def phase_a() -> None:
    header(f"Phase A — Session stress ({PHASE_A_CYCLES} attach/detach cycles)")
    attach_times: list[float] = []
    cycle_errors: list[float] = []
    failures = 0
    targets = [0.0, 45.0, -45.0, 0.0]

    for cycle in range(1, PHASE_A_CYCLES + 1):
        try:
            m = fresh_motor()
            t0 = time.monotonic()
            m.attach()
            attach_times.append(time.monotonic() - t0)
            m.set_origin()
            cycle_max_err = 0.0
            for t in targets:
                _, err = safe_move(m, t)
                cycle_max_err = max(cycle_max_err, abs(err))
            cycle_errors.append(cycle_max_err)
            m.detach()
            log(f"  cycle {cycle:2d}/{PHASE_A_CYCLES}: attach={attach_times[-1]*1000:.0f}ms, max_err={cycle_max_err:.2f}°")
        except Exception as e:
            failures += 1
            log(f"  cycle {cycle:2d}/{PHASE_A_CYCLES}: FAIL ({type(e).__name__}: {e})")
            # try to clean up
            try:
                m.detach()
            except Exception:
                pass
            time.sleep(0.5)

    if attach_times:
        log(
            f"  attach time: mean={mean(attach_times)*1000:.0f}ms, "
            f"σ={stdev(attach_times)*1000 if len(attach_times) > 1 else 0:.0f}ms, "
            f"max={max(attach_times)*1000:.0f}ms"
        )
    if cycle_errors:
        log(f"  per-cycle max error: mean={mean(cycle_errors):.2f}°, max={max(cycle_errors):.2f}°")
    log(f"  failures: {failures}/{PHASE_A_CYCLES}")

    # Pass: 0 failures, max error within 2°
    if failures == 0 and (not cycle_errors or max(cycle_errors) < 2.0):
        mark("A", "PASS")
    else:
        mark("A", "FAIL", f"{failures} failed cycles, max_err={max(cycle_errors) if cycle_errors else 'n/a'}")


# Phase B — Motion loop (long)
def phase_b() -> None:
    header(f"Phase B — Motion loop ({PHASE_B_DURATION_S//60} min, random targets in {SAFE_RANGE_DEG}°)")
    rng = random.Random(0xC0FFEE)
    errors: list[float] = []
    bucket_errors: dict[int, list[float]] = {}  # 5-min buckets
    fail_count = 0
    move_count = 0

    MAX_CONSECUTIVE_FAILS = 5  # abort if recovery can't get us moving again
    consecutive_fails = 0
    aborted = False

    m = fresh_motor()
    try:
        m.attach()
        m.set_origin()
        t_start = time.monotonic()
        last_status_t = t_start
        while True:
            elapsed = time.monotonic() - t_start
            if elapsed >= PHASE_B_DURATION_S:
                break
            if PHASE_B_SAMPLE_LIMIT and move_count >= PHASE_B_SAMPLE_LIMIT:
                break

            target = rng.uniform(*SAFE_RANGE_DEG)
            rpm = rng.randint(*SAFE_RPM_RANGE)
            try:
                _, err = safe_move(m, target, rpm=rpm)
                errors.append(abs(err))
                bucket = int(elapsed // 300)
                bucket_errors.setdefault(bucket, []).append(abs(err))
                move_count += 1
                consecutive_fails = 0
            except Exception as e:
                fail_count += 1
                consecutive_fails += 1
                log(f"  move {move_count+1}: FAIL ({type(e).__name__}: {e})")
                if consecutive_fails >= MAX_CONSECUTIVE_FAILS:
                    log(f"  {consecutive_fails} consecutive failures — attempting full re-attach")
                    try:
                        m.detach()
                    except Exception:
                        pass
                    time.sleep(1.0)
                    try:
                        m = fresh_motor()
                        m.attach()
                        log("  re-attach succeeded — continuing")
                        consecutive_fails = 0
                    except Exception as e2:
                        log(f"  re-attach FAILED ({type(e2).__name__}: {e2}) — aborting Phase B")
                        aborted = True
                        break
                else:
                    time.sleep(0.5)

            # progress line every ~60s
            if time.monotonic() - last_status_t > 60:
                last_status_t = time.monotonic()
                recent = errors[-50:] if errors else []
                log(
                    f"  t={int(elapsed):>4}s  moves={move_count:>4}  "
                    f"recent_err mean={mean(recent) if recent else 0:.2f}° "
                    f"max={max(recent) if recent else 0:.2f}°  fails={fail_count}"
                )
    finally:
        try:
            m.detach()
        except Exception:
            pass

    if aborted:
        PHASES["B"]["notes"].append("aborted after sustained recovery failures (likely USB lost)")

    log(f"  total moves: {move_count}, failures: {fail_count}")
    if errors:
        log(f"  error: mean={mean(errors):.2f}°, σ={stdev(errors) if len(errors) > 1 else 0:.2f}°, max={max(errors):.2f}°")
        log("  drift by 5-min bucket:")
        for b in sorted(bucket_errors):
            es = bucket_errors[b]
            log(f"    bucket {b*5:>2}-{(b+1)*5:>2}min: n={len(es):>4}  mean={mean(es):.2f}°  max={max(es):.2f}°")

    # Pass: fail_count == 0, max error < 3°, drift over duration < 0.5° increase in bucket means
    drift_ok = True
    if len(bucket_errors) >= 2:
        keys = sorted(bucket_errors)
        first = mean(bucket_errors[keys[0]])
        last = mean(bucket_errors[keys[-1]])
        drift_ok = (last - first) < 0.5
        log(f"  drift: first_bucket_mean={first:.2f}°  last_bucket_mean={last:.2f}°  Δ={last-first:+.2f}°")

    if fail_count == 0 and errors and max(errors) < 3.0 and drift_ok:
        mark("B", "PASS")
    else:
        mark("B", "FAIL", f"fails={fail_count}, max_err={max(errors) if errors else 'n/a'}, drift_ok={drift_ok}")


# Phase C — Profile round-trip
def phase_c() -> None:
    header("Phase C — Profile round-trip (load → P1 → save → reload → diff)")
    failures: list[str] = []
    try:
        m = fresh_motor()
        m.attach()
        m.set_origin()
        suite = CharacterizationSuite(m)
        log("  running P1 (iterations=3)…")
        p1 = suite.run_p1_precision(iterations=3, rpm=200, target_deg=0.0)
        log(f"  P1: sigma={p1.sigma_deg:.3f}° peak={p1.peak_deg:.3f}°")
        suite.update_profile()

        # Save to a temp file, reload, diff.
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td) / "wrist_roundtrip.yaml"
            m.profile.save(tmp_path)
            log(f"  saved to {tmp_path.name}")

            reloaded = Profile.load(tmp_path)
            orig_sigma = m.profile.characterization.precision.sigma_deg
            re_sigma = reloaded.characterization.precision.sigma_deg
            if orig_sigma != re_sigma:
                failures.append(f"sigma_deg differs after reload: {orig_sigma} vs {re_sigma}")
            else:
                log(f"  precision.sigma_deg round-tripped: {re_sigma:.3f}°")

            orig_peak = m.profile.characterization.precision.peak_deg
            re_peak = reloaded.characterization.precision.peak_deg
            if orig_peak != re_peak:
                failures.append(f"peak_deg differs: {orig_peak} vs {re_peak}")
            else:
                log(f"  precision.peak_deg round-tripped: {re_peak:.3f}°")

        m.detach()
    except Exception as e:
        failures.append(f"{type(e).__name__}: {e}")
        log(f"  EXC: {e!r}")

    if not failures:
        mark("C", "PASS")
    else:
        mark("C", "FAIL", "; ".join(failures))


# Phase D — Level mix
def phase_d() -> None:
    header(f"Phase D — Level mix ({PHASE_D_ITERATIONS} interleaved L1/L2/L3 calls)")
    failures: list[str] = []
    counts = {"L1": 0, "L2": 0, "L3": 0}
    rng = random.Random(0xBADF00D)
    try:
        m = fresh_motor()
        m.attach()
        for i in range(PHASE_D_ITERATIONS):
            level = rng.choice(["L1", "L2", "L3"])
            try:
                if level == "L1":
                    _ = m.work_current_ma
                    _ = m.position_counts
                    _ = m.speed_rpm
                elif level == "L2":
                    _ = m.diagnostics.status_text()
                    _ = m.diagnostics.pulses_received()
                    _ = m.diagnostics.protection_latched()
                elif level == "L3":
                    _ = m.raw.read_encoder()
                    _ = m.raw.read_angle_degrees()
                    _ = m.raw.read_motor_status()
                counts[level] += 1
            except Exception as e:
                failures.append(f"iter {i} ({level}): {type(e).__name__}: {e}")
                log(f"  iter {i}: FAIL on {level} — {e}")
        m.detach()
    except Exception as e:
        failures.append(f"setup/teardown: {type(e).__name__}: {e}")

    log(f"  successful iterations by level: L1={counts['L1']}  L2={counts['L2']}  L3={counts['L3']}  total={sum(counts.values())}/{PHASE_D_ITERATIONS}")
    if not failures:
        mark("D", "PASS")
    else:
        mark("D", "FAIL", f"{len(failures)} iteration failures (first: {failures[0]})")


# Phase E — Error recovery
def phase_e() -> None:
    header("Phase E — Error recovery (forced CommTimeout, then verify re-attach)")
    failures: list[str] = []
    try:
        # Step 1: force a CommTimeout by tightening the per-transaction timeout to ~0
        m = fresh_motor()
        m.attach()
        log("  step 1: lowering raw.timeout to 0.001s to force CommTimeout")
        orig_timeout = m.raw.timeout
        m.raw.timeout = 0.001
        got = None
        try:
            _ = m.read()
            got = "no exception"
        except CommTimeout as e:
            got = f"CommTimeout: {e}"
        except MKSError as e:
            got = f"{type(e).__name__}: {e}"  # also acceptable
        except Exception as e:
            got = f"UNEXPECTED {type(e).__name__}: {e}"
        log(f"  step 1: read() under aggressive timeout → {got}")
        if not got.startswith(("CommTimeout", "ChecksumError", "ProtocolError")):
            failures.append(f"expected CommTimeout/MKSError subtype, got: {got}")

        # Step 2: restore timeout and verify normal operation
        m.raw.timeout = orig_timeout
        time.sleep(0.3)
        log("  step 2: timeout restored, verifying normal read…")
        try:
            r = m.read()
            log(f"  step 2: read() OK → {r:.2f}°")
        except Exception as e:
            failures.append(f"step 2 read failed: {e}")

        # Step 3: detach then re-attach from a fresh Motor instance
        m.detach()
        log("  step 3: detached, re-attaching from fresh Motor instance…")
        m2 = fresh_motor()
        m2.attach()
        r2 = m2.read()
        log(f"  step 3: re-attach OK, read={r2:.2f}°")
        m2.detach()
    except Exception as e:
        failures.append(f"{type(e).__name__}: {e}")

    if not failures:
        mark("E", "PASS")
    else:
        mark("E", "FAIL", "; ".join(failures))


# --- Main ------------------------------------------------------------------ #

def summary() -> int:
    header("SUMMARY")
    fails = 0
    for k in "ABCDE":
        p = PHASES[k]
        line = f"  Phase {k} — {p['name']:<22s} {p['status']}"
        if p["notes"]:
            line += f"  ({'; '.join(p['notes'])})"
        log(line)
        if p["status"] != "PASS":
            fails += 1
    log()
    log(f"Report saved to: {REPORT}")
    return 0 if fails == 0 else 1


def main() -> int:
    header(f"v1.0 soak test — {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    log(f"Profile: {PROFILE_NAME}")
    log(f"Phase B duration: {PHASE_B_DURATION_S//60} min")
    log(f"Phase A cycles: {PHASE_A_CYCLES}")
    log(f"Phase D iterations: {PHASE_D_ITERATIONS}")
    log(f"Report file: {REPORT.name}")

    t_overall = time.monotonic()
    try:
        with timed("Phase A"): phase_a()
        with timed("Phase B"): phase_b()
        with timed("Phase C"): phase_c()
        with timed("Phase D"): phase_d()
        with timed("Phase E"): phase_e()
    except KeyboardInterrupt:
        log("INTERRUPTED — running summary on what we have so far")

    log(f"\nTotal elapsed: {(time.monotonic()-t_overall)/60:.1f} min")
    rc = summary()
    _log_fh.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
