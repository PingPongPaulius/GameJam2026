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

LIGHT_FRAME_ID = "body_light_weight"
REINFORCED_FRAME_ID = "body_reinforced"
HEAVY_FRAME_ID = "body_heavy_duty"

# Frame tiers: higher number = stronger. An engine is safe if the rocket's
# best frame tier is >= the engine's required tier.
FRAME_TIER = {
    LIGHT_FRAME_ID: 1,
    REINFORCED_FRAME_ID: 2,
    HEAVY_FRAME_ID: 3,
}
TIER_LIGHT = 1
TIER_REINFORCED = 2
TIER_HEAVY = 3

# (engine_id, required_frame_tier, speed_limit)
# Checked strongest-first so the harshest unmet requirement wins.
STRUCTURAL_ENGINE_LIMITS = (
    ("heavy_booster_engine", TIER_HEAVY, 700.0),
    ("vector_engine", TIER_HEAVY, 500.0),
    ("medium_engine", TIER_REINFORCED, 400.0),
    ("vacuum_engine", TIER_LIGHT, 300.0),
    ("small_efficient_engine", TIER_LIGHT, 250.0),
)


@dataclass(frozen=True)
class FlightFailure:
    kind: str  # "overheat" | "hard_landing" | "tumble" | "structural" | "other"
    severity: float  # 0..1+ for VFX scale


def check_flight_failure(
    rocket,
    *,
    landed: bool = False,
    impact_speed: float = 0.0,
    force_failure: bool = False,
) -> Optional[FlightFailure]:
    """Return the first applicable failure, or None if still flying safely."""
    structural = _check_structural(rocket)
    if structural:
        return structural

    overheat = _check_overheat(rocket)
    if overheat:
        return overheat

    tumble = _check_tumble(rocket)
    if tumble:
        return tumble

    if landed:
        return _check_hard_landing(impact_speed)

    if force_failure:
        return FlightFailure(kind="other", severity=0.5)

    return None


def _part_ids(rocket) -> set[str]:
    return {p.part_def.id for p in rocket.parts}


def _best_frame_tier(ids: set[str]) -> int:
    return max((FRAME_TIER[part_id] for part_id in ids if part_id in FRAME_TIER), default=0)


def _check_structural(rocket) -> Optional[FlightFailure]:
    """Engine vs frame speed limits — underbuilt airframes tear apart."""
    ids = _part_ids(rocket)
    speed = rocket.velocity
    frame_tier = _best_frame_tier(ids)

    for engine_id, required_tier, speed_limit in STRUCTURAL_ENGINE_LIMITS:
        if engine_id not in ids:
            continue
        if frame_tier >= required_tier:
            continue
        if speed <= speed_limit:
            continue
        severity = min(2.0, speed / speed_limit)
        return FlightFailure(kind="structural", severity=severity)

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
