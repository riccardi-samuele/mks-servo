# mks-servo

Python library for **MKS SERVO42D** RS485 closed-loop stepper drivers.
Built for robotics and automation: progressive-disclosure API, multi-motor
buses, profile-driven configuration, and a hardware characterization suite.

```{toctree}
:maxdepth: 2
:caption: Getting Started

quickstart
profiles
multi-motor
characterization
```

```{toctree}
:maxdepth: 2
:caption: Reference

api
faq
```

## API levels at a glance

| Level | Surface         | Audience                                           |
|-------|-----------------|----------------------------------------------------|
| L0    | `Motor`         | Lifecycle: `attach` / `detach` / `write` / `read`. |
| L1    | `Motor`         | Properties + motion: `move_relative`, `mode`, etc. |
| L2    | `motor.advanced`, `motor.diagnostics` | Driver-flash ops, health.       |
| L3    | `motor.raw`     | Per-opcode `RawDriver` for protocol work.          |

## Install

```bash
pip install mks-servo
```

## Status

Released as **1.0.0** on 2026-05-19. HIL-validated on a real NEMA17 +
SERVO42D + 12&nbsp;V rig: motion loop, profile round-trip, all four API
levels, and a forced-error recovery path all green across a five-phase soak.

## License

Apache License 2.0 — see [LICENSE](https://github.com/riccardi-samuele/mks-servo/blob/master/LICENSE).
