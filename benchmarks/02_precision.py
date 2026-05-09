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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
        rand_deg = random.uniform(-180.0, 180.0)
        m.move_absolute_axis(degrees_to_encoder_counts(rand_deg), rpm=300, acc=10)
        m.wait_until_idle(timeout=10.0)

        m.move_absolute_axis(target_counts, rpm=300, acc=10)
        m.wait_until_idle(timeout=10.0)

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

    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    residuals = np.array([r["residual_deg"] for r in rows])
    sigma = float(np.std(residuals, ddof=1))
    peak = float(np.max(np.abs(residuals)))
    print(f"  σ = {sigma:.4f}°,  peak = {peak:.4f}°")

    fig, ax = plt.subplots()
    ax.hist(residuals, bins=30)
    ax.set_xlabel("residual [deg]")
    ax.set_ylabel("count")
    ax.set_title(f"P1 repeatability  σ={sigma:.4f}°  peak={peak:.4f}°  (n={iters})")
    fig.tight_layout()
    fig.savefig(run_dir / "plots" / "p1_repeatability_hist.png", dpi=120)
    plt.close(fig)
    print(f"  → {csv_path.name} + p1_repeatability_hist.png")


def run_p3(m: MKSServo42D, run_dir: Path, iters: int = 20) -> None:
    """P3: error vs speed — final residual after a 1-turn move at varying RPM."""
    banner(f"P3: error vs speed (iters per RPM = {iters})")
    rpms = [50, 100, 300, 600, 1000, 1500, 2000, 3000]
    csv_path = run_dir / "p3_error_vs_speed.csv"
    rows = []

    m.move_absolute_axis(0, rpm=300, acc=10)
    m.wait_until_idle(timeout=15.0)

    for rpm in rpms:
        for i in range(iters):
            origin = m.read_encoder_addition()
            target = origin + degrees_to_encoder_counts(360.0)
            acc = 10 if rpm <= 800 else 50
            m.move_absolute_axis(target, rpm=rpm, acc=acc)
            m.wait_until_idle(timeout=20.0)
            time.sleep(0.05)
            measured = m.read_encoder_addition()
            residual_counts = measured - target
            residual_deg = encoder_counts_to_degrees(residual_counts)
            rows.append({"rpm": rpm, "iter": i, "residual_deg": residual_deg})
        last = [r["residual_deg"] for r in rows[-iters:]]
        rms = float(np.sqrt(np.mean(np.square(last))))
        peak = float(np.max(np.abs(last)))
        print(f"  rpm={rpm:>4}  RMS={rms:.4f}°  peak={peak:.4f}°")

    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rpm", "iter", "residual_deg"])
        w.writeheader()
        w.writerows(rows)

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


def run_p5(m: MKSServo42D, run_dir: Path, iters: int = 1) -> None:
    """P5: follow error — poll cmd 0x39 during a slow 1-turn move."""
    banner("P5: follow error (1 turn @ 60 RPM)")
    csv_path = run_dir / "p5_follow_error.csv"
    rows = []

    origin = m.read_encoder_addition()
    target = origin + degrees_to_encoder_counts(360.0)
    m.move_absolute_axis(target, rpm=60, acc=2)
    t0 = time.monotonic()
    deadline = t0 + 15.0
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

    # Safety: if we exited via deadline (not target reached), make sure motor stops.
    try:
        m.wait_until_idle(timeout=3.0)
    except Exception:
        m.emergency_stop()
        time.sleep(0.5)

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


TEST_FUNCS = {"P1": run_p1, "P3": run_p3, "P5": run_p5, "V1": run_v1}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests", default="P1,P3,P5,V1", help="Comma-separated test ids")
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
