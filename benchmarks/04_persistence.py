"""04_persistence: configuration persistence across power-cycles (C1, C2, C3).

Usage: python benchmarks/04_persistence.py [--tests C1,C2,C3]
Hardware required. ⚠ asks user to physically power-cycle the 12V (USB stays connected).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from mks_servo import MKSServo42D
from mks_servo.constants import WorkMode
from mks_servo.driver import degrees_to_encoder_counts
from benchmarks._common import banner, confirm, load_config, make_run_dir


def _open(cfg, addr_override: int | None = None) -> MKSServo42D:
    return MKSServo42D(
        port=cfg["serial"]["port"], baud=cfg["serial"]["baud"],
        addr=addr_override if addr_override else cfg["serial"]["slave_addr"],
        timeout=cfg["serial"]["timeout"],
    )


def run_c1(cfg, run_dir: Path) -> None:
    banner("C1: full config diff across power-cycle")
    with _open(cfg) as m:
        cfg_pre = m.read_all_config()
        (run_dir / "c1_pre.json").write_text(json.dumps(
            {**{k: v for k, v in cfg_pre.items() if k != "raw"},
             "raw_hex": cfg_pre["raw"].hex()}, indent=2))
    confirm("Disconnect 12V from the motor, wait 3 seconds, reconnect.")
    time.sleep(0.5)
    with _open(cfg) as m:
        cfg_post = m.read_all_config()
        (run_dir / "c1_post.json").write_text(json.dumps(
            {**{k: v for k, v in cfg_post.items() if k != "raw"},
             "raw_hex": cfg_post["raw"].hex()}, indent=2))
    same = cfg_pre["raw"] == cfg_post["raw"]
    diff_path = run_dir / "c1_diff.txt"
    if same:
        diff_path.write_text("PASS — pre and post raw match.\n")
        print("  PASS")
    else:
        lines = ["FAIL — bytes differ:"]
        for i, (a, b) in enumerate(zip(cfg_pre["raw"], cfg_post["raw"])):
            if a != b:
                lines.append(f"  byte {i}: pre=0x{a:02X}  post=0x{b:02X}")
        diff_path.write_text("\n".join(lines) + "\n")
        print("  FAIL — see c1_diff.txt")


def run_c2(cfg, run_dir: Path) -> None:
    banner("C2: calibration persists")
    confirm("Mark the shaft. Then press ENTER to do 10 turns BEFORE power-cycle.")
    with _open(cfg) as m:
        m.set_work_mode(WorkMode.SR_vFOC)
        m.enable(True)
        origin = m.read_encoder_addition()
        m.move_absolute_axis(origin + 10 * 0x4000, rpm=180, acc=20)
        m.wait_until_idle(timeout=30.0)
        end_pre = m.read_encoder_addition()
        turns_pre = (end_pre - origin) / 0x4000
        m.enable(False)
    print(f"  encoder reports {turns_pre:.4f} turns BEFORE power-cycle")
    confirm("Disconnect 12V, wait 3 s, reconnect. Pointer should be back near start mark.")
    time.sleep(0.5)
    with _open(cfg) as m:
        m.set_work_mode(WorkMode.SR_vFOC)
        m.enable(True)
        origin = m.read_encoder_addition()
        m.move_absolute_axis(origin + 10 * 0x4000, rpm=180, acc=20)
        m.wait_until_idle(timeout=30.0)
        end_post = m.read_encoder_addition()
        turns_post = (end_post - origin) / 0x4000
        m.enable(False)
    print(f"  encoder reports {turns_post:.4f} turns AFTER power-cycle (no recalibration)")
    (run_dir / "c2_calibration.txt").write_text(
        f"Pre  : {turns_pre:.6f} turns\nPost : {turns_post:.6f} turns\n"
        "Visual: confirmed by user (manual)\n"
    )


def run_c3(cfg, run_dir: Path) -> None:
    banner("C3: custom params survive power-cycle")
    target_current = 2200
    target_subdiv = 64
    target_addr = 7
    original_addr = cfg["serial"]["slave_addr"]

    with _open(cfg) as m:
        m.set_work_current_ma(target_current)
        m.set_subdivision(target_subdiv)
        from mks_servo.constants import OpCode
        m._txn(OpCode.SET_SLAVE_ADDR, bytes([target_addr]), expect_payload_len=1)
    confirm("Disconnect 12V, wait 3 s, reconnect.")
    time.sleep(0.5)

    try:
        with _open(cfg, addr_override=target_addr) as m:
            cfg_post = m.read_all_config()
        ok = (cfg_post["current_ma"] == target_current
              and cfg_post["subdivision"] == target_subdiv
              and cfg_post["slave_addr"] == target_addr)
        line = (f"current={cfg_post['current_ma']} subdiv={cfg_post['subdivision']} "
                f"addr={cfg_post['slave_addr']} -> {'PASS' if ok else 'FAIL'}")
        print(f"  {line}")
        (run_dir / "c3_custom_params.txt").write_text(line + "\n")
    finally:
        banner("C3 cleanup: restoring slave address")
        try:
            with _open(cfg, addr_override=target_addr) as m:
                from mks_servo.constants import OpCode
                m._txn(OpCode.SET_SLAVE_ADDR, bytes([original_addr]), expect_payload_len=1)
            print(f"  restored slave addr -> {original_addr}")
        except Exception as e:
            print(f"  ⚠ failed to restore addr: {e}\n  Manually set UartAddr={original_addr} from menu.")


TEST_FUNCS = {"C1": run_c1, "C2": run_c2, "C3": run_c3}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests", default="C1,C2,C3")
    args = parser.parse_args()
    cfg = load_config()
    run_dir = make_run_dir("persistence")
    print(f"Output dir: {run_dir}")
    for tid in [t.strip().upper() for t in args.tests.split(",")]:
        fn = TEST_FUNCS.get(tid)
        if fn:
            fn(cfg, run_dir)
        else:
            print(f"  (skipping {tid})")
    print(f"\nDone. Artifacts in {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
