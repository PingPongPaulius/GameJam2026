"""Flight failure predicates — pure logic, no pygame."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import math


# Tunable thresholds — adjust to feel.
MAX_HEAT = 50.0
HARD_LANDING_SPEED = 40.0  # m/s downward at touchdown
TUMBLE_ANGLE = math.pi / 2  # ~90° from upright
TUMBLE_SPIN = 4.0  # rad/s — fast spin counts even before fully inverted


@dataclass(frozen=True)
class FlightFailure:
    kind: str  # "overheat" | "hard_landing" | "tumble"
    severity: float  # 0..1+ for VFX scale


def check_flight_failure(
    rocket,
    *,
    landed: bool = False,
    impact_speed: float = 0.0,
) -> Optional[FlightFailure]:
    """Return the first applicable failure, or None if still flying safely."""
    overheat = _check_overheat(rocket)
    if overheat:
        return overheat

    tumble = _check_tumble(rocket)
    if tumble:
        return tumble

    if landed:
        return _check_hard_landing(impact_speed)

    return None


def _check_overheat(rocket) -> Optional[FlightFailure]:
    if rocket.heat < MAX_HEAT:
        return None
    severity = min(2.0, rocket.heat / MAX_HEAT)
    return FlightFailure(kind="overheat", severity=severity)


def _check_tumble(rocket) -> Optional[FlightFailure]:
    # Normalize to [-pi, pi] so upright wraps cleanly.
    angle = (rocket.rotation + math.pi) % (2 * math.pi) - math.pi
    spun_out = abs(rocket.rotation_speed) >= TUMBLE_SPIN
    inverted = abs(angle) >= TUMBLE_ANGLE
    if not (inverted or spun_out):
        return None
    severity = min(2.0, abs(angle) / math.pi + abs(rocket.rotation_speed) / TUMBLE_SPIN * 0.5)
    return FlightFailure(kind="tumble", severity=max(0.8, severity))


def _check_hard_landing(impact_speed: float) -> Optional[FlightFailure]:
    speed = abs(impact_speed)
    if speed < HARD_LANDING_SPEED:
        return None
    severity = min(2.0, speed / HARD_LANDING_SPEED)
    return FlightFailure(kind="hard_landing", severity=severity)
