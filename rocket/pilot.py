from dataclasses import dataclass, field

@dataclass
class PilotAttributes:
    fuel_consumption: float = 1.0

@dataclass
class Pilot:
    name: str
    attributes: PilotAttributes = field(default_factory=PilotAttributes)