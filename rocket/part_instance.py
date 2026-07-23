from dataclasses import dataclass
from rocket.part_data import PartDef

@dataclass
class PartInstance:
    part_def: PartDef
    slot_index: int
    offset_x: float = 0.0
    rotation: float = 0.0
