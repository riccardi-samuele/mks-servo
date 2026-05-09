"""Shared helpers for benchmark scripts: config loading, output dirs, CSV/log writers."""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import tomllib  # py >= 3.11
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


REPO_ROOT = Path(__file__).resolve().parent.parent
RESULTS_ROOT = REPO_ROOT / "results"
CONFIG_PATH = REPO_ROOT / "config.toml"


def load_config() -> dict:
    with CONFIG_PATH.open("rb") as f:
        return tomllib.load(f)


def make_run_dir(bench_name: str) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = RESULTS_ROOT / f"{bench_name}_{ts}"
    (d / "plots").mkdir(parents=True, exist_ok=True)
    return d


def open_csv(path: Path, fieldnames: list[str]):
    f = path.open("w", newline="")
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    return f, w


def append_jsonl(path: Path, record: dict) -> None:
    with path.open("a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def banner(msg: str) -> None:
    print(f"\n=== {msg} ===", flush=True)


def confirm(prompt: str) -> None:
    """Pause for manual user action (used by persistence tests)."""
    print(f"\n[ACTION REQUIRED] {prompt}", flush=True)
    input("Press ENTER when done...")


from typing import Any, Callable, TypeVar
from mks_servo.exceptions import CommTimeout

T = TypeVar("T")


def safe_call(fn: Callable[..., T], *args: Any, retries: int = 1, **kwargs: Any) -> T:
    """Call `fn(*args, **kwargs)` and retry once on CommTimeout.

    USB-RS485 adapters sometimes drop the first byte after a long pause; one
    retry recovers the transaction in practice. Re-raises after `retries`.
    """
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return fn(*args, **kwargs)
        except CommTimeout as e:
            last_exc = e
    assert last_exc is not None
    raise last_exc
