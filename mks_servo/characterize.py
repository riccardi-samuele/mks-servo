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


import math


def _stats(samples: list[float], target: float) -> tuple[float, float, float]:
    """Return (mean, sigma, peak_abs_dev_from_target)."""
    n = len(samples)
    if n == 0:
        return 0.0, 0.0, 0.0
    mean = sum(samples) / n
    var = sum((s - mean) ** 2 for s in samples) / n
    sigma = math.sqrt(var)
    peak = max(abs(s - target) for s in samples)
    return mean, sigma, peak


def _rms(values: list[float]) -> float:
    if not values:
        return 0.0
    return math.sqrt(sum(v * v for v in values) / len(values))


# Methods bound to CharacterizationSuite below:

def _run_p1_precision(self, *,
                      target_deg: float = 0.0,
                      iterations: int = 5,
                      rpm: int = 300) -> P1Result:
    """Move to target N times and measure the read-back spread.

    Returns a P1Result with samples, mean, sigma, peak.
    """
    samples: list[float] = []
    for _ in range(iterations):
        self._motor.write(target_deg, rpm=rpm)
        samples.append(self._motor.read())
    mean, sigma, peak = _stats(samples, target_deg)
    res = P1Result(
        target_deg=target_deg, iterations=iterations,
        samples_deg=samples, mean_deg=mean,
        sigma_deg=sigma, peak_deg=peak,
    )
    self._last_results.p1 = res
    return res


def _run_p3_error_vs_rpm(self, *,
                         rpms: Optional[list[int]] = None,
                         samples_per_rpm: int = 5,
                         target_deg: float = 90.0) -> P3Result:
    """For each RPM, do `samples_per_rpm` writes to `target_deg` and measure
    the RMS of (read - target)."""
    if rpms is None:
        rpms = [50, 100, 300, 500, 1000]
    rms_per_rpm: list[float] = []
    for rpm in rpms:
        errs: list[float] = []
        for _ in range(samples_per_rpm):
            self._motor.write(target_deg, rpm=rpm)
            errs.append(self._motor.read() - target_deg)
        rms_per_rpm.append(_rms(errs))
    res = P3Result(rpm_samples=list(rpms), rms_error_deg=rms_per_rpm)
    self._last_results.p3 = res
    return res


CharacterizationSuite.run_p1_precision = _run_p1_precision
CharacterizationSuite.run_p3_error_vs_rpm = _run_p3_error_vs_rpm
