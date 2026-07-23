from rocket.part_types import PartType
from rocket.pilot import Pilot
from rocket.part_instance import PartInstance

class Rocket:
    def __init__(self, pilot: Pilot):
        self.pilot = pilot
        self.parts: list[PartInstance] = []

        self.height = 0.0
        self.velocity = 0.0
        self.rotation = 0.0
        self.heat = 0.0
        self.fuel_remaining = 0.0

    def add_part(self, part: PartInstance):
        self.parts.append(part)

    def remove_part(self, part: PartInstance):
        if part in self.parts:
            self.parts.remove(part)

    def part_at_slot(self, slot_index: int, offset_x: float = 0.0):
        for p in self.parts:
            if p.slot_index == slot_index and abs(p.offset_x - offset_x) < 0.01:
                return p
        return None

    def reset(self):
        self.parts.clear()
        self.height = self.velocity = self.rotation = self.heat = 0.0
        self.fuel_remaining = 0.0

    @property
    def total_weight(self) -> float:
        return sum(p.part_def.weight for p in self.parts)

    @property
    def total_thrust(self) -> float:
        return sum(p.part_def.thrust for p in self.parts)
    @property
    def total_fuel_capacity(self) -> float:
        return sum(p.part_def.fuel_capacity for p in self.parts)

    @property
    def total_heat_dissipation(self) -> float:
        return sum(p.part_def.heat_dissipation for p in self.parts)

    @property
    def stability(self) -> float:
        """
        Stability from part contributions, reduced by horizontal offset, vertical
        center-of-mass drift, and overall horizontal mass imbalance.
        """
        if not self.parts:
            return 0.0

        side_types = {PartType.FIN, PartType.BOOSTER}
        total = 0.0
        center_weight = 0.0
        horizontal_weighted = 0.0

        for p in self.parts:
            if p.part_def.part_type in side_types:
                total += p.part_def.stability_contribution
                continue

            offset_ratio = min(1.0, abs(p.offset_x) / 64.0)
            contribution = p.part_def.stability_contribution * (1.0 - offset_ratio)
            asymmetry_penalty = offset_ratio * 2.5
            total += contribution - asymmetry_penalty

            horizontal_weighted += p.offset_x * p.part_def.weight
            center_weight += p.part_def.weight

        com = self._center_of_mass_slot()
        min_slot = min(p.slot_index for p in self.parts)
        max_slot = max(p.slot_index for p in self.parts)
        total -= abs(com - (min_slot + max_slot) / 2) * 0.75

        if center_weight > 0:
            horizontal_com = horizontal_weighted / center_weight
            total -= min(1.0, abs(horizontal_com) / 64.0) * 1.5

        return max(0.0, total)

    @property
    def center_of_mass_slot(self) -> float:
        if not self.parts:
            return 0.0
        return self._center_of_mass_slot()

    def _center_of_mass_slot(self) -> float:
        weighted = sum(p.slot_index * p.part_def.weight for p in self.parts)
        return weighted / self.total_weight

    @property
    def fuel_consumption_rate(self) -> float:
        base_rate = self.total_thrust * 0.05
        return base_rate * self.pilot.attributes.fuel_consumption

    def validate(self) -> list[str]:
        errors = []
        if not self.parts:
            return ["Rocket has no parts."]
        if not any(p.part_def.part_type == PartType.ENGINE for p in self.parts):
            errors.append("Missing an engine.")
        if not any(p.part_def.part_type == PartType.NOSE_CONE for p in self.parts):
            errors.append("Missing a nose cone.")
        return errors

    def is_launch_ready(self) -> bool:
        return len(self.validate()) == 0
                    