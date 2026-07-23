import pygame
from rocket.part_instance import PartInstance
from rocket.part_types import PartType
from ui.drag_state import DragState

SIDE_MOUNT_TYPES = {PartType.FIN, PartType.BOOSTER}
COUNTDOWN_SECONDS = 30

class BuildScene:
    def __init__(self, rocket, sidebar, build_area, assets, audio=None,
                 countdown_seconds=COUNTDOWN_SECONDS, on_timeout=None):
        self.rocket = rocket
        self.sidebar = sidebar
        self.build_area = build_area
        self.assets = assets
        self.audio = audio
        self.drag = DragState()
        self.time_remaining = countdown_seconds
        self.on_timeout = on_timeout
        self._done = False

    def handle_event(self, event): 
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            item = self.sidebar.item_at(event.pos)
            if item:
                self.drag.start(item.part_def, event.pos)

        elif event.type == pygame.MOUSEMOTION and self.drag.active:
            is_side = self.drag.part_def.part_type in SIDE_MOUNT_TYPES
            slot, offset_x = self.build_area.slot_at(event.pos, side_mount=is_side)
            self.drag.update(event.pos, slot, offset_x)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.drag.active:
            self._try_place()
            self.drag.cancel()

    def _try_place(self):
        slot = self.drag.target_slot
        if slot is None:
            return
        if self._position_occupied(slot, self.drag.target_offset_x):
            return
        if not self._is_valid_placement(slot, self.drag.target_offset_x, self.drag.part_def):
            return
        self.rocket.add_part(PartInstance(
            part_def=self.drag.part_def,
            slot_index=slot,
            offset_x=self.drag.target_offset_x,
        ))
        if self.audio:
            self.audio.play("part_place")

    def _is_valid_placement(self, slot, offset_x, part_def) -> bool:
        if not self.rocket.parts:
            return True
        is_side = part_def.part_type in SIDE_MOUNT_TYPES
        return self._connects_to_existing(slot, offset_x, is_side)

    def _connects_to_existing(self, slot, offset_x, is_side) -> bool:
        occupied_rows = {p.slot_index for p in self.rocket.parts}
        center_rows = {
            p.slot_index for p in self.rocket.parts
            if p.part_def.part_type not in SIDE_MOUNT_TYPES
        }

        if is_side:
            return slot in center_rows

        if slot in occupied_rows:
            return True

        return any(abs(slot - row) == 1 for row in occupied_rows)

    def _position_occupied(self, slot, offset_x):
        return any(
            p.slot_index == slot and abs(p.offset_x - offset_x) < 0.01
            for p in self.rocket.parts
        )

    def update(self, dt):
        if self._done:
            return
        self.time_remaining = max(0.0, self.time_remaining - dt)
        if self.time_remaining == 0:
            self._done = True
            if self.on_timeout:
                self.on_timeout()

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        if not self.drag.active:
            self.sidebar.update_hover(mouse_pos)
        else:
            self.sidebar.palette.hovered_item = None

        self.sidebar.draw(surface)
        self.build_area.draw(surface)
        for instance in self.rocket.parts:
            pos = self.build_area.slot_screen_pos(instance.slot_index, instance.offset_x)
            image = self.assets.get_image(instance.part_def.sprite)
            surface.blit(image, image.get_rect(center=pos))

        if self.drag.active:
            image = self.assets.get_image(self.drag.part_def.sprite).copy()
            image.set_alpha(150)
            surface.blit(image, image.get_rect(center=self.drag.mouse_pos))
            if self.drag.target_slot is not None:
                pos = self.build_area.slot_screen_pos(
                    self.drag.target_slot,
                    self.drag.target_offset_x,
                )
                valid = self._is_valid_placement(
                    self.drag.target_slot,
                    self.drag.target_offset_x,
                    self.drag.part_def,
                )
                color = (0, 255, 0) if valid else (255, 80, 80)
                pygame.draw.circle(surface, color, (int(pos[0]), int(pos[1])), 5)

        font = pygame.font.SysFont(None, 36)
        timer_surf = font.render(f"{self.time_remaining:0.1f}s", True, (255, 255, 255))
        stability_surf = font.render(f"Stability: {self.rocket.stability:.1f}", True, (255, 255, 255))
        center_x = self.sidebar.width + (surface.get_width() - self.sidebar.width) // 2
        surface.blit(timer_surf, (center_x - 30, 20))
        surface.blit(stability_surf, (center_x - 70, 55))

        if not self.drag.active:
            self.sidebar.draw_tooltip(surface)
