import json
from dataclasses import dataclass
from pathlib import Path

from rocket.part_types import PartType

DEFAULT_PARTS_PATH = Path("data/parts_new.json")


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
    fuel_consumption: float = 0.0
    sprite: str = ""
    gimbal: bool = False
    cone: bool = False
    drag_reduction_factor: float = 1.0


def parse_part_catalog(raw: dict) -> dict[str, PartDef]:
    catalog = {}
    for e in raw.get("parts", []):
        part = PartDef(
            id=e["id"],
            name=e["name"],
            part_type=PartType[e["part_type"]],
            weight=e["weight"],
            thrust=e.get("thrust", 0.0),
            drag=e.get("drag", 0.0),
            fuel_capacity=e.get("fuel_capacity", 0.0),
            stability_contribution=e.get("stability_contribution", 0.0),
            heat_dissipation=e.get("heat_dissipation", 0.0),
            fuel_consumption=e.get("fuel_consumption", 0.0),
            sprite=e.get("sprite", ""),
            gimbal=e.get("gimbal", False),
            cone=e.get("cone", False),
            drag_reduction_factor=e.get("drag_reduction_factor", 1.0),
        )
        catalog[part.id] = part
    return catalog


def set_part_catalog(catalog: dict[str, PartDef]) -> None:
    PART_CATALOG.clear()
    PART_CATALOG.update(catalog)


def load_part_catalog_from_file(path: str | Path = DEFAULT_PARTS_PATH) -> dict[str, PartDef]:
    with open(path, encoding="utf-8") as f:
        return parse_part_catalog(json.load(f))


PART_CATALOG: dict[str, PartDef] = {}
