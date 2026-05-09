"""Temporary back-compat shim for the v0.1.0 refactor.

Re-exports the public symbols of `mks_servo.raw` under the old module path
`mks_servo.driver`, so existing benchmarks that did
`from mks_servo.driver import ...` keep working without code changes.

Removed in Task 36 of the v0.1.0 implementation plan.
"""
from mks_servo.raw import (  # noqa: F401
    MotorStatus,
    RawDriver,
    MKSServo42D,
    degrees_to_encoder_counts,
    encoder_counts_to_degrees,
    degrees_to_pulses,
)
