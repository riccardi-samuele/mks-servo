"""CharacterizationSuite: programmatic empirical tests that populate
profile.characterization."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from mks_servo.motor import Motor


@dataclass
class P1Result:
    """Repeatability — same target N times, measure read-back spread."""
    target_deg: float
    iterations: int
    samples_deg: list[float]
    mean_deg: float
    sigma_deg: float
    peak_deg: float


@dataclass
class P3Result:
    """Error vs commanded RPM."""
    rpm_samples: list[int]
    rms_error_deg: list[float]


@dataclass
class P5Result:
    """Follow error during a sweep at constant RPM."""
    rpm: int
    duration_s: float
    max_follow_err_deg: float
    rms_follow_err_deg: float


@dataclass
class S2Result:
    """Acceleration curves to target RPM with varying acc parameter."""
    target_rpm: int
    accs: list[int]
    time_to_target_ms: list[Optional[float]]
    max_observed_rpm: int


@dataclass
class SuiteResult:
    p1: Optional[P1Result] = None
    p3: Optional[P3Result] = None
    p5: Optional[P5Result] = None
    s2: Optional[S2Result] = None


class CharacterizationSuite:
    """Programmatic characterization tests for an attached Motor.

    Usage:
        with Motor.from_profile("wrist") as m:
            suite = CharacterizationSuite(m)
            results = suite.run_mvp()
            suite.update_profile()
            m.profile.save()
    """

    def __init__(self, motor: "Motor", *, output_dir: Optional[Path] = None):
        self._motor = motor
        self._output_dir = output_dir
        self._last_results = SuiteResult()

    # Test methods are added in Tasks 5-7.
