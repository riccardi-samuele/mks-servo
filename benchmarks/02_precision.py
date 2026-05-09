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
