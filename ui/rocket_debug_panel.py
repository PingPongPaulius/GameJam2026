import pygame


class RocketDebugPanel:
    MARGIN = 16
    PADDING = 12
    LINE_HEIGHT = 22

    def __init__(self):
        self._title_font = pygame.font.SysFont(None, 26)
        self._label_font = pygame.font.SysFont(None, 22)
        self._value_font = pygame.font.SysFont(None, 22)

    def _stat_lines(self, rocket, in_flight: bool = False) -> list[tuple[str, str]]:
        lines = [
            ("Parts", str(len(rocket.parts))),
            ("Weight", f"{rocket.total_weight:.1f}"),
            ("Thrust", f"{rocket.total_thrust:.0f}"),
            ("Drag", f"{rocket.total_drag:.0f}"),
            ("Performance", f"{rocket.performance:.1f}"),
            ("Velocity", f"{rocket.velocity:.1f}"),
            ("Height", f"{rocket.height:.0f}"),
            (
                "Fuel",
                f"{rocket.fuel_remaining:.0f} / {rocket.total_fuel_capacity:.0f}",
            ),
            ("Heat", f"{rocket.heat:.1f}"),
            ("Stability", f"{rocket.stability:.1f}"),
            ("Fuel use/s", f"{rocket.fuel_consumption_rate:.2f}"),
        ]
        if rocket.parts:
            lines.append(("CoM slot", f"{rocket.center_of_mass_slot:.2f}"))
        if in_flight:
            status = "Flying"
        else:
            status = "Ready" if rocket.is_launch_ready() else "Incomplete"
        lines.append(("Status", status))
        return lines

    def draw(self, surface, rocket, in_flight: bool = False):
        lines = self._stat_lines(rocket, in_flight)
        panel_w = 220
        title_height = 28
        panel_h = self.PADDING * 2 + title_height + len(lines) * self.LINE_HEIGHT

        panel_x = surface.get_width() - panel_w - self.MARGIN
        panel_y = surface.get_height() - panel_h - self.MARGIN
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        shadow = panel_rect.move(2, 2)
        pygame.draw.rect(surface, (10, 12, 18), shadow, border_radius=8)

        panel = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
        panel.fill((22, 26, 34, 230))
        surface.blit(panel, panel_rect.topleft)
        pygame.draw.rect(surface, (90, 110, 140), panel_rect, 2, border_radius=8)

        x = panel_rect.x + self.PADDING
        y = panel_rect.y + self.PADDING

        title = self._title_font.render("Rocket Stats", True, (200, 220, 245))
        surface.blit(title, (x, y))
        y += title_height

        pygame.draw.line(
            surface,
            (65, 75, 95),
            (panel_rect.x + self.PADDING, y - 6),
            (panel_rect.right - self.PADDING, y - 6),
            1,
        )

        for label, value in lines:
            label_surf = self._label_font.render(label, True, (160, 175, 195))
            value_surf = self._value_font.render(value, True, (235, 240, 248))
            surface.blit(label_surf, (x, y))
            surface.blit(
                value_surf,
                (panel_rect.right - self.PADDING - value_surf.get_width(), y),
            )
            y += self.LINE_HEIGHT
