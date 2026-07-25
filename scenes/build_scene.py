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

        self.lock_after_seconds = countdown_seconds
        self.elapsed = 0.0
        self._locked = False
        self.last_placed = 0

    def reset(self, countdown_seconds=None):
        """Return to a fresh build round."""
        if countdown_seconds is not None:
            self.lock_after_seconds = countdown_seconds
        self.time_remaining = self.lock_after_seconds
        self.elapsed = 0.0
        self._done = False
        self._locked = False
        self.drag.cancel()
        self.sidebar.unlock_palette()

    def handle_event(self, event): 
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            item = self.sidebar.item_at(event.pos)
            if item:
                self.drag.start(item.part_def, event.pos)

        elif event.type == pygame.MOUSEMOTION and self.drag.active:
            is_side = self.drag.part_def.part_type in SIDE_MOUNT_TYPES
            host_offset_x = 0.0
            if is_side:
                host_offset_x = self._host_offset_at(event.pos)
            slot, offset_x = self.build_area.slot_at(
                event.pos,
                side_mount=is_side,
                host_offset_x=host_offset_x,
            )
            self.drag.update(event.pos, slot, offset_x)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.drag.active:
            self._try_place()
            self.drag.cancel()

    def _try_place(self):
        slot = self.drag.target_slot
        self.last_placed = self.elapsed
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

    def _center_hosts_in_slot(self, slot):
        return [
            p for p in self.rocket.parts
            if p.slot_index == slot and p.part_def.part_type not in SIDE_MOUNT_TYPES
        ]

    def _host_offset_at(self, mouse_pos) -> float:
        """Offset of the nearest center part in the hovered slot (else 0)."""
        mx, my = mouse_pos
        rel_y = self.build_area.anchor_y - my
        slot = round(rel_y / self.build_area.slot_height)
        hosts = self._center_hosts_in_slot(slot)
        if not hosts:
            return 0.0
        return min(
            hosts,
            key=lambda p: abs(self.build_area.anchor_x + p.offset_x - mx),
        ).offset_x

    def _connects_to_existing(self, slot, offset_x, is_side) -> bool:
        occupied_rows = {p.slot_index for p in self.rocket.parts}
        hosts = self._center_hosts_in_slot(slot)

        if is_side:
            # Must sit beside a center part in this row.
            return any(
                abs(abs(offset_x - p.offset_x) - self.build_area.side_attach_offset) < 0.01
                for p in hosts
            )

        if slot in occupied_rows:
            return True

        return any(abs(slot - row) == 1 for row in occupied_rows)

    def _position_occupied(self, slot, offset_x):
        return any(
            p.slot_index == slot and abs(p.offset_x - offset_x) < 0.01
            for p in self.rocket.parts
        )

    def _side_faces_left(self, slot, offset_x) -> bool:
        hosts = self._center_hosts_in_slot(slot)
        if hosts:
            host = min(hosts, key=lambda p: abs(p.offset_x - offset_x))
            return offset_x < host.offset_x
        return offset_x < 0

    def _part_image(self, part_def, offset_x=0.0, slot=None):
        image = self.assets.get_image(part_def.sprite)
        if part_def.part_type not in SIDE_MOUNT_TYPES:
            return image
        faces_left = (
            self._side_faces_left(slot, offset_x)
            if slot is not None
            else offset_x < 0
        )
        if not faces_left:
            return pygame.transform.flip(image, True, False)
        return image

    def update(self, dt):
        if self._done:
            return
        self.time_remaining = max(0.0, self.time_remaining - dt)
        self.elapsed += dt
        if self.time_remaining == 0:
            if not self._locked:
                self.sidebar.lock_palette()
                self._locked = True
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
            image = self._part_image(
                instance.part_def,
                instance.offset_x,
                slot=instance.slot_index,
            )
            surface.blit(image, image.get_rect(center=pos))

        if self.drag.active:
            if self.drag.target_slot is not None:
                pos = self.build_area.slot_screen_pos(
                    self.drag.target_slot,
                    self.drag.target_offset_x,
                )
                valid = (
                    not self._position_occupied(
                        self.drag.target_slot,
                        self.drag.target_offset_x,
                    )
                    and self._is_valid_placement(
                        self.drag.target_slot,
                        self.drag.target_offset_x,
                        self.drag.part_def,
                    )
                )
                image = self._part_image(
                    self.drag.part_def,
                    self.drag.target_offset_x,
                    slot=self.drag.target_slot,
                ).copy()
                image.set_alpha(150)
                surface.blit(image, image.get_rect(center=pos))
                color = (0, 255, 0) if valid else (255, 80, 80)
                pygame.draw.circle(surface, color, (int(pos[0]), int(pos[1])), 5)
            else:
                image = self.assets.get_image(self.drag.part_def.sprite).copy()
                image.set_alpha(120)
                surface.blit(image, image.get_rect(center=self.drag.mouse_pos))

        font = pygame.font.SysFont(None, 36)
        timer_surf = font.render(f"{self.time_remaining:0.1f}s", True, (255, 255, 255))
        stability_surf = font.render(f"Stability: {self.rocket.stability:.1f}", True, (255, 255, 255))
        center_x = self.sidebar.width + (surface.get_width() - self.sidebar.width) // 2
        surface.blit(timer_surf, (center_x - 30, 20))
        surface.blit(stability_surf, (center_x - 70, 55))

        if not self.drag.active:
            self.sidebar.draw_tooltip(surface)
