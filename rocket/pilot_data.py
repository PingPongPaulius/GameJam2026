import json
from dataclasses import dataclass

@dataclass(frozen=True)
class PilotDef:
    id: str
    name: str
    attributes: dict[str, str]
    avatar: str = ""

def load_pilots(path="data/pilots.json") -> dict[str, PilotDef]:
    with open(path) as f:
        raw = json.load(f)
    catalog = {}
    for e in raw["pilots"]:
        pilot = PilotDef(
            id=e["id"], name=e["name"],
            attributes=e["attributes"],
            avatar=e.get("avatar", ""),
        )
        catalog[pilot.id] = pilot
    return catalog

PILOT_CATALOG = load_pilots()