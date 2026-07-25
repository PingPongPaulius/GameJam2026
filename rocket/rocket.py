import math
from rocket.part_types import PartType
from rocket.pilot import Pilot
from rocket.part_instance import PartInstance

class Rocket:
    VERTICAL_UNIT = 8.0  # physical distance per slot_index step, for COG/COT/inertia math only (not rendering)

    def __init__(self, pilot: Pilot):
        self.pilot = pilot
        self.parts: list[PartInstance] = []

        self.height = 0.0
        self.x_position = 0.0
        self.x_velocity = 0.0
        self.y_velocity = 0.0
        self.velocity = 0.0
        self.rotation = 0.0 #0 to 2pi 0 being straight up, pi being upside down, 2pi being straight up again
        self.heat = 0.0
        self.fuel_remaining = 0.0
        self.fuel_weight_per_unit = 0.5  # in tons per ton of fuel in the tank
        self.x_acceleration = 0.0
        self.y_acceleration = 0.0
        self.acceleration = 0.0
        self.rotation_speed = 0.0
        self.rotation_acceleration = 0.0
        self.rotation_damping = 0.0
        self.rotation_inertia = 0.0
        self.COM_x = 0.0
        self.COT_x= 0.0
        self.drag_reduction_factor = 1.0

    @property
    def min_drag_reduction_factor(self) -> float:
        if not self.parts:
            return 1.0
        return min(p.part_def.drag_reduction_factor for p in self.parts if p.part_def.cone)

    def add_part(self, part: PartInstance):
        self.parts.append(part)
        print(f"Added part {part.part_def.name} at slot {part.slot_index} with xoffset {part.offset_x} slot index {part.slot_index}") #temp debug :)

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
        self.height = self.x_velocity = self.y_velocity = self.rotation = self.heat = 0.0
        self.fuel_remaining = 0.0

    @property
    def fuel_percentage(self) -> float:
        if self.total_fuel_capacity <= 0:
            return 0.0
        return self.fuel_remaining / self.total_fuel_capacity

    @property  # in tons
    def total_weight(self) -> float:
        return sum(p.part_def.weight for p in self.parts)

    @property  # in kN
    def total_thrust(self) -> float:
        return sum(p.part_def.thrust for p in self.parts) if self.fuel_remaining > 0 else 0

    @property
    def total_drag(self) -> float:
        return sum(p.part_def.drag for p in self.parts)

    @property  # in tons of fuel
    def total_fuel_capacity(self) -> float:
        return sum(p.part_def.fuel_capacity for p in self.parts)

    @property
    def total_heat_dissipation(self) -> float:
        return sum(p.part_def.heat_dissipation for p in self.parts)

    @property
    def total_fuel_consumption(self) -> float:  # tons per second
        return sum(p.part_def.fuel_consumption for p in self.parts)

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
        if self.total_weight <= 0:
            return 0.0
        weighted = sum(p.slot_index * p.part_def.weight for p in self.parts)
        return weighted / self.total_weight

    def _part_effective_mass(self, p: PartInstance) -> float:
        total_capacity = self.total_fuel_capacity  # max tons across all tanks, not fuel_percentage
        if total_capacity > 0 and p.part_def.fuel_capacity > 0:
            share = p.part_def.fuel_capacity / total_capacity
            return p.part_def.weight + self.fuel_weight * share
        return p.part_def.weight

    def _center_of_gravity_y_scaled(self) -> float:
        total_mass = sum(self._part_effective_mass(p) for p in self.parts)
        if total_mass <= 0:
            return 0.0
        return sum(
            (p.slot_index * 64.0 / self.VERTICAL_UNIT) * self._part_effective_mass(p)
            for p in self.parts
        ) / total_mass

    @property
    def center_of_gravity_y(self) -> float:
        if not self.parts:
            return 0.0
        return self._center_of_gravity_y_scaled()

    @property
    def center_of_gravity_x(self) -> float:
        if not self.parts:
            return 0.0
        total_mass = sum(self._part_effective_mass(p) for p in self.parts)
        if total_mass <= 0:
            return 0.0
        return sum(
            (p.offset_x / self.VERTICAL_UNIT) * self._part_effective_mass(p)
            for p in self.parts
        ) / total_mass

    @property
    def center_of_thrust_x(self) -> float:
        total_thrust = sum(p.part_def.thrust for p in self.parts)
        if total_thrust <= 0:
            return 0.0
        return sum(
            (p.offset_x / self.VERTICAL_UNIT) * p.part_def.thrust for p in self.parts
        ) / total_thrust

    @property
    def moment_of_inertia(self) -> float:
        if not self.parts:
            return 0.0
        cog_x = self.center_of_gravity_x
        cog_y = self._center_of_gravity_y_scaled()
        total = 0.0
        for p in self.parts:
            mass = self._part_effective_mass(p)
            dx = (p.offset_x / self.VERTICAL_UNIT) - cog_x
            dy = (p.slot_index * 64.0 / self.VERTICAL_UNIT) - cog_y
            total += mass * (dx * dx + dy * dy)
        return total

    @property
    def fuel_consumption_rate(self) -> float:
        # Pilot attribute multipliers are not applied to flight yet.
        return self.total_fuel_consumption

    @property
    def fuel_weight(self) -> float:
        return self.fuel_remaining * self.fuel_weight_per_unit

    @property
    def power(self) -> float:
        # Yes, it has a magic number, what does it mean? Yes.
        return math.sqrt(self.total_thrust) * 250.0;

    @property
    def mass(self) -> float:
        return self.total_weight + self.fuel_weight

    @property
    def aerodynamics(self) -> float:
        # Oh no, another magic number! Maybe I should just do this in the physics engine?
        return max(0.4, 1 - self.total_drag / 100)

    @property
    def fuel_bonus(self) -> float:
        # Oh no, another magic number! Maybe I should just do this in the physics engine?
        return 1 + (self.total_fuel_capacity / 250)

    @property
    def performance(self) -> float:
        if self.mass <= 0:
            return 0.0
        return (self.power * self.aerodynamics * self.fuel_bonus) / self.mass

    def validate(self) -> list[str]:
        errors = []
        if not self.parts:
            return ["Rocket has no parts."]
        if not any(p.part_def.part_type == PartType.ENGINE for p in self.parts):
            errors.append("Missing an engine.")
        if not any(p.part_def.part_type == PartType.FUEL_TANK for p in self.parts):
            errors.append("Missing a fuel tank.")
        if not any(p.part_def.part_type == PartType.NOSE_CONE for p in self.parts):
            errors.append("Missing a nose cone.")
        return errors

    def is_launch_ready(self) -> bool:
        return len(self.validate()) == 0
    
    def apply_pilot_modifiers(self):
        print("Apply")
    

    def apply_pilot_effects(self, data):
        print(data)
        if self.pilot.mission(data):
            self.apply_pilot_modifiers()

    def render(self, surface, assets, pos):
        for instance in self.parts:
            image = assets.get_image(instance.part_def.sprite)
            surface.blit(image, image.get_rect(center=pos))
