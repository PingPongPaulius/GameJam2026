import json
from dataclasses import dataclass

@dataclass(frozen=True)
class PilotDef:
    id: str
    name: str
    attributes: dict[str, str]
    avatar: str = ""
    mission: int = 0

def load_pilots(path="data/pilots.json") -> dict[str, PilotDef]:
    with open(path) as f:
        raw = json.load(f)
    catalog = {}
    for e in raw["pilots"]:
        pilot = PilotDef(
            id=e["id"], name=e["name"],
            attributes=e["attributes"],
            avatar=e.get("avatar", ""),
            mission=e.get("mission", 0),
        )
        catalog[pilot.id] = pilot
    return catalog

PILOT_CATALOG = load_pilots()
