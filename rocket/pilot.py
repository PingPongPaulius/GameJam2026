from dataclasses import dataclass, field
from typing import Any

def default_mission(data):
    return True

def mission_alien(data) -> bool:
    return data.get('time', 0) < 10

def mission_human(data) -> bool:
    return data.get('part_types', 0) >= 5

def mission_robot(data) -> bool:
    return data.get('battery', False) == 0 

@dataclass
class PilotAttributes:
    fuel_consumption: float = 0.0
    weight_reduction: float = 0.0
    thrust_increase: float = 0.0
    drag_efficiency: float = 0.0

@dataclass
class Pilot:
    name: str
    attributes: PilotAttributes = field(default_factory=PilotAttributes)
    portrait_sprite: str = "pilots/pilot-1.gif"
    mission: Any = mission_alien
