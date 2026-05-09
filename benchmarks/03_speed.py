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
        for cmd_rpm in np.arange(50, int(max_rated * 1.1), 100, dtype=int).tolist() + [max_rated]:
            m.move_speed(rpm=int(cmd_rpm), acc=10, direction=Direction.CW)
            time.sleep(2.5)
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
