"""01_smoke: verify communication, dump config, optionally calibrate.

Usage: python benchmarks/01_smoke.py [--calibrate]
Hardware required.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mks_servo import Motor
from mks_servo.constants import WorkMode
from mks_servo.profile import Profile, DriverSection, TransportSection
from benchmarks._common import banner, load_config, make_run_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibrate", action="store_true",
                        help="Run encoder calibration (motor MUST be unloaded)")
    args = parser.parse_args()

    cfg = load_config()
    run_dir = make_run_dir("smoke")
    print(f"Output dir: {run_dir}")

    prof = Profile(
        id="bench_smoke",
        driver=DriverSection(model="servo42d", slave_addr=cfg["serial"]["slave_addr"]),
        transport=TransportSection(
            port=cfg["serial"]["port"],
            baud=cfg["serial"]["baud"],
            timeout_s=cfg["serial"]["timeout"],
        ),
    )
    with Motor(prof) as m:
        banner("Step 1: ping (read encoder)")
        carry, value = m.raw.read_encoder()
        print(f"  encoder: carry={carry}, value=0x{value:04X} ({value})")

        banner("Step 2: read full config snapshot")
        snap = m.raw.read_all_config()
        print(json.dumps({k: v for k, v in snap.items() if k != "raw"}, indent=2))
        (run_dir / "config_snapshot.json").write_text(
            json.dumps({**{k: v for k, v in snap.items() if k != "raw"},
                        "raw_hex": snap["raw"].hex()}, indent=2)
        )

        banner("Step 3: motor status")
        print(f"  status = {m.status.name}")

        banner("Step 4: ensure SR_vFOC mode + 16 microsteps")
        m.raw.set_work_mode(WorkMode.SR_vFOC)
        m.microsteps = 16

        if args.calibrate:
            banner("Step 5: CALIBRATING (motor must be unloaded)")
            m.calibrate()
            print("  calibration OK (re-read config to verify):")
            print(json.dumps({k: v for k, v in m.raw.read_all_config().items() if k != "raw"}, indent=2))
        else:
            print("  (skipping calibration; pass --calibrate to run it)")

    print(f"\nSmoke OK. Artifacts in {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
