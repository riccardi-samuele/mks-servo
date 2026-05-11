"""Programmatic characterization example.

Usage:
    python examples/characterize_motor.py [profile-id]

Default profile id: wrist.
"""
import sys
from mks_servo import Motor, CharacterizationSuite


def main(profile_id: str = "wrist") -> None:
    with Motor.from_profile(profile_id) as m:
        suite = CharacterizationSuite(m)
        results = suite.run_mvp()
        print("=== Results ===")
        if results.p1:
            print(f"P1 precision: sigma={results.p1.sigma_deg:.4f}°, "
                  f"peak={results.p1.peak_deg:.4f}°")
        if results.p3:
            for rpm, rms in zip(results.p3.rpm_samples,
                                results.p3.rms_error_deg):
                print(f"P3 @ {rpm:>4d} RPM: rms={rms:.4f}°")
        if results.p5:
            print(f"P5 follow @ {results.p5.rpm} RPM: "
                  f"max={results.p5.max_follow_err_deg:.3f}°")
        if results.s2:
            print(f"S2 max observed RPM: {results.s2.max_observed_rpm}")

        suite.update_profile()
        m.profile.save()
        print(f"profile updated and saved to {m.profile.path}")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "wrist"
    main(arg)
