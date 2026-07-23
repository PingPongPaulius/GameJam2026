import json
from dataclasses import dataclass
from rocket.part_types import PartType

@dataclass(frozen=True)
class PartDef:
    id: str
    name: str
    part_type: PartType
    weight: float
    thrust: float = 0.0
    drag: float = 0.0
    fuel_capacity: float = 0.0
    stability_contribution: float = 0.0
    heat_dissipation: float = 0.0
    sprite: str = ""

def load_part_catalog(path="data/parts.json") -> dict[str, PartDef]:
    with open(path) as f:
        raw = json.load(f)
    catalog = {}
    for e in raw["parts"]:
        part = PartDef(
            id=e["id"], name=e["name"],
            part_type=PartType[e["part_type"]],
            weight=e["weight"],
            thrust=e.get("thrust", 0.0),
            drag=e.get("drag", 0.0),
            fuel_capacity=e.get("fuel_capacity", 0.0),
            stability_contribution=e.get("stability_contribution", 0.0),
            heat_dissipation=e.get("heat_dissipation", 0.0),
            sprite=e.get("sprite", ""),
        )
        catalog[part.id] = part
    return catalog

PART_CATALOG = load_part_catalog()