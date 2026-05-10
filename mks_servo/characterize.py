"""CharacterizationSuite: programmatic empirical tests that populate
profile.characterization."""
from __future__ import annotations

import time as _time
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


def _run_p5_follow_error(self, *,
                         rpm: int = 60,
                         duration_s: float = 2.0,
                         sweep_deg: float = 360.0,
                         sample_interval_s: float = 0.05) -> P5Result:
    """Move at constant RPM and sample motor.error() throughout the sweep."""
    # Setup move: get to start position.
    self._motor.write(0.0, rpm=rpm, blocking=True)
    # Start the sweep non-blocking; sample errors during it.
    self._motor.write(sweep_deg, rpm=rpm, blocking=False)
    samples: list[float] = []
    t0 = _time.monotonic()
    while _time.monotonic() - t0 < duration_s:
        try:
            samples.append(abs(self._motor.error()))
        except Exception:
            break
        _time.sleep(sample_interval_s)
    try:
        self._motor.wait_until_idle()
    except Exception:
        pass
    max_err = max(samples) if samples else 0.0
    rms_err = _rms(samples)
    res = P5Result(rpm=rpm, duration_s=duration_s,
                   max_follow_err_deg=max_err,
                   rms_follow_err_deg=rms_err)
    self._last_results.p5 = res
    return res


def _run_s2_acceleration(self, *,
                         target_rpm: int = 2000,
                         accs: Optional[list[int]] = None,
                         samples_per_acc: int = 50,
                         sample_interval_s: float = 0.01,
                         cool_s: float = 1.0) -> S2Result:
    """For each acc value, command move_speed to target_rpm and time to plateau.

    Uses motor.raw.move_speed (Level 3) — Motor doesn't expose velocity mode
    directly. Returns the time-to-target (ms) for each acc and the maximum
    observed RPM across the runs.
    """
    if accs is None:
        accs = [1, 50, 100, 200, 255]
    times: list[Optional[float]] = []
    max_rpm = 0
    for acc in accs:
        # Reset to zero rpm
        try:
            self._motor.raw.move_speed(rpm=0, acc=255, direction=0)
        except Exception:
            pass
        _time.sleep(cool_s)
        # Start ramp
        try:
            self._motor.raw.move_speed(rpm=int(target_rpm),
                                       acc=int(acc), direction=0)
        except Exception:
            times.append(None)
            continue
        t0 = _time.monotonic()
        reached: Optional[float] = None
        for _ in range(samples_per_acc):
            v = abs(self._motor.speed_rpm)
            if v > max_rpm:
                max_rpm = v
            if v >= target_rpm * 0.95:
                reached = (_time.monotonic() - t0) * 1000.0
                break
            _time.sleep(sample_interval_s)
        times.append(reached)
        try:
            self._motor.raw.move_speed(rpm=0, acc=255, direction=0)
        except Exception:
            pass
    res = S2Result(target_rpm=target_rpm, accs=list(accs),
                   time_to_target_ms=times,
                   max_observed_rpm=int(max_rpm))
    self._last_results.s2 = res
    return res


CharacterizationSuite.run_p5_follow_error = _run_p5_follow_error
CharacterizationSuite.run_s2_acceleration = _run_s2_acceleration
