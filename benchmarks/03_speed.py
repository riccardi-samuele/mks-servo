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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


def run_s2(m: MKSServo42D, run_dir: Path) -> None:
    """S2: acceleration curve — sample read_speed_rpm() while ramping to 2000 RPM."""
    banner("S2: acceleration curve (target 2000 RPM)")
    m.enable(False)
    m.set_work_mode(WorkMode.SR_vFOC)
    m.enable(True)
    target_rpm = 2000
    accs = [1, 50, 100, 200, 255]
    csv_path = run_dir / "s2_accel.csv"
    rows = []

    for acc in accs:
        m.move_speed(rpm=0, acc=255, direction=Direction.CW)
        time.sleep(1.0)
        m.move_speed(rpm=target_rpm, acc=acc, direction=Direction.CW)
        t0 = time.monotonic()
        while True:
            v = abs(m.read_speed_rpm())
            t = (time.monotonic() - t0) * 1000
            rows.append({"acc": acc, "t_ms": int(t), "rpm": v})
            if v >= target_rpm or t > 8000:
                break
            time.sleep(0.01)
        m.move_speed(rpm=0, acc=255, direction=Direction.CW)
        time.sleep(1.5)

    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["acc", "t_ms", "rpm"])
        w.writeheader()
        w.writerows(rows)

    fig, ax = plt.subplots()
    for acc in accs:
        sub = [r for r in rows if r["acc"] == acc]
        ax.plot([r["t_ms"] for r in sub], [r["rpm"] for r in sub], label=f"acc={acc}")
        if acc < 256:
            t_max = max(r["t_ms"] for r in sub)
            ts = np.linspace(0, t_max, 50)
            vs = np.minimum(target_rpm, ts / ((256 - acc) * 0.05))
            ax.plot(ts, vs, "--", alpha=0.4)
    ax.set_xlabel("time [ms]")
    ax.set_ylabel("measured RPM")
    ax.set_title("S2: ramp to 2000 RPM (solid=measured, dashed=theoretical)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(run_dir / "plots" / "s2_accel.png", dpi=120)
    plt.close(fig)


def run_s3(m: MKSServo42D, run_dir: Path) -> None:
    """S3: stall threshold — 10-turn move at increasing RPM in SR_CLOSE mode."""
    banner("S3: stall threshold")
    m.enable(False)
    m.set_work_mode(WorkMode.SR_CLOSE)
    m.set_subdivision(16)
    m.enable(True)
    rpms = [500, 1000, 1300, 1500, 1700, 2000, 2500]
    csv_path = run_dir / "s3_stall.csv"
    rows = []

    m.move_absolute_axis(0, rpm=300, acc=20)
    m.wait_until_idle(timeout=15.0)

    for rpm in rpms:
        try:
            origin = m.read_encoder_addition()
            target = origin + 10 * 0x4000
            m.move_absolute_axis(target, rpm=rpm, acc=50)
            m.wait_until_idle(timeout=30.0)
            time.sleep(0.3)
            measured = m.read_encoder_addition()
            residual_counts = measured - target
            residual_deg = encoder_counts_to_degrees(residual_counts)
            angle_err_units = m.read_angle_error()
            print(f"  rpm={rpm:>4}  residual={residual_deg:+.4f}°  angle_err={angle_err_units}")
            rows.append({"rpm": rpm, "residual_deg": residual_deg,
                         "angle_err_units": angle_err_units, "ok": abs(residual_deg) < 1.0})
        except Exception as e:
            print(f"  rpm={rpm}  FAILED: {e}")
            rows.append({"rpm": rpm, "residual_deg": float("nan"),
                         "angle_err_units": -1, "ok": False})
            try:
                m.release_protection()
                m.move_absolute_axis(0, rpm=300, acc=20)
                m.wait_until_idle(timeout=15.0)
            except Exception:
                pass

    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rpm", "residual_deg", "angle_err_units", "ok"])
        w.writeheader()
        w.writerows(rows)

    fig, ax = plt.subplots()
    ax.plot([r["rpm"] for r in rows], [abs(r["residual_deg"]) for r in rows], marker="o")
    ax.axhline(1.0, color="r", linestyle="--", alpha=0.5, label="1° threshold")
    ax.set_xlabel("RPM")
    ax.set_ylabel("|residual after 10 turns| [deg]")
    ax.set_title("S3: stall threshold (SR_CLOSE)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(run_dir / "plots" / "s3_stall.png", dpi=120)
    plt.close(fig)


TEST_FUNCS = {"S1": run_s1, "S2": run_s2, "S3": run_s3}


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
