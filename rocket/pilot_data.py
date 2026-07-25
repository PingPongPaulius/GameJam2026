import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PILOTS_PATH = Path("data/pilots.json")


@dataclass(frozen=True)
class PilotDef:
    id: str
    name: str
    attributes: dict[str, str]
    avatar: str = ""
    mission: int = 0


_ATTR_DEFAULTS = {
    "fuel_consumption": 1.0,
    "weight_reduction": 1.0,
    "thrust_increase": 1.0,
    "drag_efficiency": 1.0,
}


def _normalize_attributes(attributes: dict | None) -> dict:
    """Fill missing attrs and treat 0 as neutral (1.0) so rocket math stays valid."""
    normalized = dict(_ATTR_DEFAULTS)
    if attributes:
        normalized.update(attributes)
    for key, default in _ATTR_DEFAULTS.items():
        try:
            if float(normalized[key]) == 0:
                normalized[key] = default
        except (TypeError, ValueError):
            normalized[key] = default
    return normalized


def parse_pilots(raw: dict) -> dict:
    catalog = {}
    for e in raw.get("pilots", []):
        pilot = PilotDef(
            id=e["id"],
            name=e["name"],
            attributes=_normalize_attributes(e.get("attributes")),
            avatar=e.get("avatar", ""),
            mission=e.get("mission", 0),
        )
        catalog[pilot.id] = pilot
    return catalog


def set_pilot_catalog(catalog: dict) -> None:
    PILOT_CATALOG.clear()
    PILOT_CATALOG.update(catalog)


def load_pilots_from_file(path: str | Path = DEFAULT_PILOTS_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return parse_pilots(json.load(f))


PILOT_CATALOG: dict = {}
