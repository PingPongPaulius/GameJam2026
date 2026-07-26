import asyncio
import inspect

import pygame

from api.highscore_client import fetch_highscores


class ScoreOverlay:
    """Modal overlay for entering a name and submitting flight results."""

    MAX_NAME_LENGTH = 32
    PANEL_W = 460
    LEADERBOARD_LIMIT = 10
    ROW_HEIGHT = 26

    def __init__(self, on_submit=None, on_restart=None):
        self.on_submit = on_submit
        self.on_restart = on_restart
        self.visible = False
        self.name = ""
        self.height = 0.0
        self.max_speed = 0.0
        self.flight_time = 0.0
        self.failure_reason = ""
        self.status = ""
        self.status_ok = None
        self.leaderboard = []
        self.leaderboard_error = ""
        self._submitting = False
        self._submitted = False
        self._loading_leaderboard = False
        self._cursor_visible = True
        self._cursor_timer = 0.0
        self._button_was_down = False

        self._title_font = pygame.font.SysFont(None, 36)
        self._reason_font = pygame.font.SysFont(None, 22)
        self._label_font = pygame.font.SysFont(None, 24)
        self._value_font = pygame.font.SysFont(None, 28)
        self._input_font = pygame.font.SysFont(None, 30)
        self._button_font = pygame.font.SysFont(None, 26)
        self._status_font = pygame.font.SysFont(None, 22)
        self._row_font = pygame.font.SysFont(None, 22)
        self._section_font = pygame.font.SysFont(None, 26)

        self._panel_rect = pygame.Rect(0, 0, self.PANEL_W, 500)
        self._input_rect = pygame.Rect(0, 0, 0, 0)
        self._submit_rect = pygame.Rect(0, 0, 0, 0)
        self._restart_rect = pygame.Rect(0, 0, 0, 0)

    def show(
        self,
        height: float,
        max_speed: float,
        flight_time: float = 0.0,
        failure_reason: str = "",
    ):
        self.visible = True
        self.name = ""
        self.height = height
        self.max_speed = max_speed
        self.flight_time = max(0.0, float(flight_time))
        self.failure_reason = failure_reason or ""
        self.status = ""
        self.status_ok = None
        self._submitting = False
        self._submitted = False
        self._loading_leaderboard = False
        self._cursor_visible = True
        self._cursor_timer = 0.0
        self._button_was_down = False
        self._schedule(self._load_leaderboard())

    def hide(self):
        self.visible = False
        self._submitting = False
        self._submitted = False
        self._loading_leaderboard = False

    @staticmethod
    def _schedule(coro):
        try:
            asyncio.get_running_loop().create_task(coro)
        except RuntimeError:
            print(f"Could not schedule async task: {coro}")

    def handle_event(self, event) -> bool:
        """Consume overlay events. Returns True if the event was handled."""
        if not self.visible:
            return False

        if self._submitting:
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._restart_rect.collidepoint(event.pos):
                self._try_restart()
                return True
            if not self._submitted and self._submit_rect.collidepoint(event.pos):
                self._try_submit()
                return True
            return True

        if self._submitted:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self._try_restart()
                return True
            return event.type in (
                pygame.KEYDOWN,
                pygame.KEYUP,
                pygame.MOUSEBUTTONDOWN,
                pygame.MOUSEBUTTONUP,
                pygame.MOUSEMOTION,
                pygame.TEXTINPUT,
            )

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._try_submit()
                return True
            if event.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
                return True
            if event.key == pygame.K_ESCAPE:
                return True

            if event.unicode and event.unicode.isprintable():
                if len(self.name) < self.MAX_NAME_LENGTH:
                    self.name += event.unicode
                return True

        return event.type in (
            pygame.KEYDOWN,
            pygame.KEYUP,
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
            pygame.MOUSEMOTION,
            pygame.TEXTINPUT,
        )

    def update(self, dt: float):
        if not self.visible:
            return

        self._cursor_timer += dt
        if self._cursor_timer >= 0.5:
            self._cursor_timer = 0.0
            self._cursor_visible = not self._cursor_visible

        if self._submitting:
            return

        mouse_down = pygame.mouse.get_pressed()[0]
        mouse_pos = pygame.mouse.get_pos()
        if mouse_down and not self._button_was_down:
            if self._restart_rect.collidepoint(mouse_pos):
                self._try_restart()
            elif not self._submitted and self._submit_rect.collidepoint(mouse_pos):
                self._try_submit()
        self._button_was_down = mouse_down

    def draw(self, surface: pygame.Surface):
        if not self.visible:
            return

        screen_w, screen_h = surface.get_size()
        dim = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        surface.blit(dim, (0, 0))

        panel_h = self._panel_height()
        self._panel_rect.size = (self.PANEL_W, panel_h)
        self._panel_rect.center = (screen_w // 2, screen_h // 2)
        panel = self._panel_rect

        shadow = panel.move(3, 3)
        pygame.draw.rect(surface, (8, 10, 14), shadow, border_radius=12)

        panel_surf = pygame.Surface(panel.size, pygame.SRCALPHA)
        panel_surf.fill((24, 28, 38, 245))
        surface.blit(panel_surf, panel.topleft)
        pygame.draw.rect(surface, (100, 125, 160), panel, 2, border_radius=12)

        x = panel.x + 28
        y = panel.y + 24
        right = panel.right - 28

        succeeded = self.height > 100_000
        title_text = "Mission successful" if succeeded else "Mission failed"
        title = self._title_font.render(title_text, True, (220, 232, 250))
        surface.blit(title, (x, y))
        y += 40

        if not succeeded and self.failure_reason:
            reason = self._reason_font.render(self.failure_reason, True, (220, 150, 140))
            surface.blit(reason, (x, y))
            y += 28

        y += 4

        for label, value in (
            ("Your height", f"{self.height:.0f} m"),
            ("Your top speed", f"{self.max_speed:.1f} m/s"),
            ("Flight time", self._format_flight_time(self.flight_time)),
        ):
            label_surf = self._label_font.render(label, True, (150, 165, 185))
            value_surf = self._value_font.render(value, True, (235, 240, 248))
            surface.blit(label_surf, (x, y))
            surface.blit(value_surf, (right - value_surf.get_width(), y - 2))
            y += 30

        y += 8
        section = self._section_font.render("Leaderboard", True, (200, 214, 235))
        surface.blit(section, (x, y))
        y += 28

        y = self._draw_leaderboard(surface, x, y, right)

        if self._submitted:
            y = self._draw_submitted_footer(surface, panel, x, y)
        else:
            y = self._draw_submit_footer(surface, panel, x, y)

        if self.status:
            if self.status_ok is True:
                color = (140, 210, 160)
            elif self.status_ok is False:
                color = (220, 130, 130)
            else:
                color = (170, 185, 210)
            status_surf = self._status_font.render(self.status, True, color)
            status_rect = status_surf.get_rect(
                centerx=panel.centerx,
                top=self._restart_rect.bottom + 12,
            )
            surface.blit(status_surf, status_rect)

    def _draw_submit_footer(self, surface, panel, x, y) -> int:
        y += 12
        name_label = self._label_font.render("Enter your name", True, (150, 165, 185))
        surface.blit(name_label, (x, y))
        y += 28

        self._input_rect = pygame.Rect(x, y, panel.width - 56, 40)
        pygame.draw.rect(surface, (14, 18, 26), self._input_rect, border_radius=6)
        pygame.draw.rect(surface, (80, 100, 130), self._input_rect, 1, border_radius=6)

        display_name = self.name
        if self._cursor_visible and not self._submitting:
            display_name += "|"
        name_surf = self._input_font.render(display_name, True, (235, 240, 248))
        surface.blit(name_surf, (self._input_rect.x + 12, self._input_rect.y + 8))

        y = self._input_rect.bottom + 18
        self._submit_rect = pygame.Rect(0, 0, 140, 42)
        self._submit_rect.centerx = panel.centerx
        self._submit_rect.y = y

        can_submit = bool(self.name.strip()) and not self._submitting
        hovered = self._submit_rect.collidepoint(pygame.mouse.get_pos())
        if self._submitting:
            btn_color = (45, 50, 60)
            border_color = (70, 80, 95)
            button_text = "Sending..."
        elif can_submit and hovered:
            btn_color = (70, 130, 90)
            border_color = (130, 200, 150)
            button_text = "Submit"
        elif can_submit:
            btn_color = (50, 100, 70)
            border_color = (100, 160, 120)
            button_text = "Submit"
        else:
            btn_color = (45, 50, 60)
            border_color = (70, 80, 95)
            button_text = "Submit"

        self._draw_button(surface, self._submit_rect, btn_color, border_color, button_text)
        return self._draw_restart_button(surface, panel, self._submit_rect.bottom + 12)

    def _draw_submitted_footer(self, surface, panel, x, y) -> int:
        self._submit_rect = pygame.Rect(0, 0, 0, 0)
        return self._draw_restart_button(surface, panel, y + 16)

    def _draw_restart_button(self, surface, panel, y: int) -> int:
        self._restart_rect = pygame.Rect(0, 0, 160, 42)
        self._restart_rect.centerx = panel.centerx
        self._restart_rect.y = y

        hovered = self._restart_rect.collidepoint(pygame.mouse.get_pos())
        if hovered and not self._submitting:
            btn_color = (70, 110, 160)
            border_color = (130, 180, 230)
        else:
            btn_color = (50, 85, 130)
            border_color = (100, 145, 195)

        self._draw_button(surface, self._restart_rect, btn_color, border_color, "Restart")
        return self._restart_rect.bottom

    def _draw_button(self, surface, rect, btn_color, border_color, button_text):
        pygame.draw.rect(surface, btn_color, rect, border_radius=8)
        pygame.draw.rect(surface, border_color, rect, 2, border_radius=8)
        label = self._button_font.render(button_text, True, (230, 240, 235))
        surface.blit(label, label.get_rect(center=rect.center))

    @staticmethod
    def _format_flight_time(seconds: float) -> str:
        seconds = max(0.0, float(seconds))
        minutes = int(seconds // 60)
        secs = seconds - minutes * 60
        if minutes > 0:
            return f"{minutes}:{secs:04.1f}"
        return f"{secs:.1f} s"

    def _panel_height(self) -> int:
        rows = max(1, len(self.leaderboard)) if not self.leaderboard_error else 1
        reason_extra = 28 if self.height <= 100_000 and self.failure_reason else 0
        if self._submitted:
            return 330 + reason_extra + rows * self.ROW_HEIGHT
        return 444 + reason_extra + rows * self.ROW_HEIGHT

    def _draw_leaderboard(self, surface, x: int, y: int, right: int) -> int:
        if self.leaderboard_error:
            error = self._row_font.render(self.leaderboard_error, True, (220, 140, 140))
            surface.blit(error, (x, y))
            return y + self.ROW_HEIGHT

        if not self.leaderboard:
            label = "Loading..." if self._loading_leaderboard else "No scores yet — be the first!"
            empty = self._row_font.render(label, True, (150, 165, 185))
            surface.blit(empty, (x, y))
            return y + self.ROW_HEIGHT

        header_rank = self._row_font.render("#", True, (120, 135, 155))
        header_name = self._row_font.render("Name", True, (120, 135, 155))
        header_height = self._row_font.render("Height", True, (120, 135, 155))
        header_speed = self._row_font.render("Speed", True, (120, 135, 155))
        surface.blit(header_rank, (x, y))
        surface.blit(header_name, (x + 28, y))
        surface.blit(header_height, (right - 170, y))
        surface.blit(header_speed, (right - header_speed.get_width(), y))
        y += self.ROW_HEIGHT

        for index, entry in enumerate(self.leaderboard, start=1):
            rank = self._row_font.render(str(index), True, (180, 195, 215))
            name = self._row_font.render(entry["name"], True, (230, 236, 248))
            height = self._row_font.render(entry["height"], True, (200, 214, 235))
            speed = self._row_font.render(entry["top_speed"], True, (200, 214, 235))
            surface.blit(rank, (x, y))
            surface.blit(name, (x + 28, y))
            surface.blit(height, (right - 170, y))
            surface.blit(speed, (right - speed.get_width(), y))
            y += self.ROW_HEIGHT

        return y

    async def _load_leaderboard(self):
        self._loading_leaderboard = True
        self.leaderboard_error = ""
        ok, result = await fetch_highscores(limit=self.LEADERBOARD_LIMIT)
        self._loading_leaderboard = False
        if not ok:
            self.leaderboard = []
            self.leaderboard_error = "Could not load leaderboard"
            print(f"Leaderboard fetch failed: {result}")
            return

        self.leaderboard_error = ""
        self.leaderboard = [self._normalize_entry(row) for row in result][: self.LEADERBOARD_LIMIT]

    @staticmethod
    def _normalize_entry(row) -> dict:
        if not isinstance(row, dict):
            return {"name": "?", "height": "-", "top_speed": "-"}

        name = str(row.get("name") or row.get("player") or "?")
        if len(name) > 16:
            name = name[:15] + "…"

        height_raw = row.get("height", row.get("score"))
        speed_raw = row.get("top_speed", row.get("max_speed"))

        try:
            height = f"{float(height_raw):.0f} m"
        except (TypeError, ValueError):
            height = "-"

        try:
            top_speed = f"{float(speed_raw):.1f}"
        except (TypeError, ValueError):
            top_speed = "-"

        return {"name": name, "height": height, "top_speed": top_speed}

    def _try_submit(self):
        name = self.name.strip()
        if not name or not self.on_submit or self._submitting or self._submitted:
            return

        self._submitting = True
        self.status = "Submitting..."
        self.status_ok = None
        self._schedule(self._submit_async(name))

    async def _submit_async(self, name: str):
        result = self.on_submit(name, self.height, self.max_speed, self.flight_time)
        if inspect.isawaitable(result):
            result = await result

        if isinstance(result, tuple) and len(result) == 2:
            ok, message = result
        elif result is False:
            ok, message = False, "Submit failed"
        else:
            ok, message = True, "Score submitted!"

        self._submitting = False
        self.status = str(message)
        self.status_ok = bool(ok)
        if ok:
            self._submitted = True
            self.status = "Updating leaderboard..."
            await self._load_leaderboard()
            self.status = "Score submitted!"

    def _try_restart(self):
        if self._submitting or not self.on_restart:
            return
        result = self.on_restart()
        if inspect.isawaitable(result):
            self._schedule(self._restart_async(result))
        else:
            self.hide()

    async def _restart_async(self, coro):
        self._submitting = True
        self.status = "Loading game data..."
        self.status_ok = None
        try:
            ok = await coro
            if ok is False:
                self.status = "Failed to reload game data"
                self.status_ok = False
                return
            self.hide()
        finally:
            self._submitting = False
