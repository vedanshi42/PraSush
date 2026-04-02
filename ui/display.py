from __future__ import annotations

import math
import sys
from pathlib import Path

import pygame

from config import AVATAR_PATH, PROJECT_NAME, WINDOW_HEIGHT, WINDOW_WIDTH

STATE_STYLES = {
    "idle": {"label": "Idle", "emoji": "Zz", "color": (120, 120, 140), "zoom": 1.0, "alpha": 130},
    "listening": {"label": "Listening", "emoji": "Mic", "color": (80, 200, 255), "zoom": 1.04, "alpha": 255},
    "thinking": {"label": "Thinking", "emoji": "AI", "color": (255, 190, 70), "zoom": 1.08, "alpha": 245},
    "speaking": {"label": "Speaking", "emoji": "Say", "color": (120, 255, 170), "zoom": 1.06, "alpha": 255},
    "greeting": {"label": "Greeting", "emoji": "Hi", "color": (255, 140, 120), "zoom": 1.12, "alpha": 255},
}


class DisplayManager:
    def __init__(self, avatar_path: Path = AVATAR_PATH) -> None:
        pygame.init()
        pygame.font.init()
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE | pygame.DOUBLEBUF)
        self.width, self.height = self.screen.get_size()
        pygame.display.set_caption(PROJECT_NAME)
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.Font(None, 56)
        self.status_font = pygame.font.Font(None, 40)
        self.hint_font = pygame.font.Font(None, 28)
        self.subtitle_font = pygame.font.Font(None, 38)
        self.avatar_surface = self._load_avatar(avatar_path)
        self.state = "idle"
        self.status_text = "Waiting for wake word"
        self.subtitle = "Say 'Hey PraSush' to begin. Press F for fullscreen, Esc to close."
        self.state_changed_at = pygame.time.get_ticks()
        self.subtitle_changed_at = pygame.time.get_ticks()

    def set_state(self, state: str, status_text: str, subtitle: str) -> None:
        if state not in STATE_STYLES:
            raise ValueError(f"Unknown UI state: {state}")
        self.state = state
        self.status_text = status_text
        self.subtitle = subtitle
        now = pygame.time.get_ticks()
        self.state_changed_at = now
        self.subtitle_changed_at = now
        self.render()

    def pump_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    app_logger.info("ESC pressed, shutting down")
                    self.close()
                if event.key == pygame.K_f:
                    self.toggle_fullscreen()
            if event.type == pygame.VIDEORESIZE and not self.is_fullscreen:
                self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE | pygame.DOUBLEBUF)
                self.width, self.height = self.screen.get_size()

    def render(self) -> None:
        tick = pygame.time.get_ticks() / 1000
        style = STATE_STYLES[self.state]
        pulse = 1 + math.sin(tick * 2.6) * 0.015
        zoom = style["zoom"] * pulse

        self.screen.fill((0, 0, 0))
        self._draw_header(style)
        self._draw_avatar(style, zoom, tick)
        self._draw_subtitle(style)
        self._draw_hint()
        pygame.display.flip()
        self.clock.tick(30)

    def close(self) -> None:
        pygame.quit()
        sys.exit(0)

    def toggle_fullscreen(self) -> None:
        self.is_fullscreen = not self.is_fullscreen
        flags = pygame.FULLSCREEN | pygame.DOUBLEBUF if self.is_fullscreen else pygame.RESIZABLE | pygame.DOUBLEBUF
        size = (0, 0) if self.is_fullscreen else (WINDOW_WIDTH, WINDOW_HEIGHT)
        self.screen = pygame.display.set_mode(size, flags)
        self.width, self.height = self.screen.get_size()
        self.render()

    def _draw_header(self, style: dict[str, object]) -> None:
        badge = str(style["emoji"])
        label = str(style["label"])
        header = f"{badge} {PROJECT_NAME} | {label}"
        title = self.title_font.render(header, True, (240, 240, 240))
        status = self.status_font.render(self.status_text, True, tuple(style["color"]))
        self.screen.blit(title, title.get_rect(center=(self.width // 2, 58)))
        self.screen.blit(status, status.get_rect(center=(self.width // 2, 106)))

    def _draw_avatar(self, style: dict[str, object], zoom: float, tick: float) -> None:
        base_width = min(self.width // 3, 500)
        aspect_ratio = self.avatar_surface.get_height() / max(self.avatar_surface.get_width(), 1)
        scaled_width = max(80, int(base_width * zoom))
        scaled_height = max(80, int(scaled_width * aspect_ratio))
        avatar = pygame.transform.smoothscale(self.avatar_surface, (scaled_width, scaled_height))
        avatar.set_alpha(int(style["alpha"]))

        glow = pygame.Surface((scaled_width + 200, scaled_height + 200), pygame.SRCALPHA)
        glow_color = tuple(style["color"])
        glow_alpha = 55 if self.state == "idle" else 115
        pygame.draw.ellipse(glow, (*glow_color, glow_alpha), glow.get_rect(), 0)

        offset_y = math.sin(tick * 2.2) * 10
        avatar_rect = avatar.get_rect(center=(self.width // 2, self.height // 2 + offset_y))
        glow_rect = glow.get_rect(center=avatar_rect.center)
        self.screen.blit(glow, glow_rect, special_flags=pygame.BLEND_RGBA_ADD)
        self.screen.blit(avatar, avatar_rect)

        ring_radius = max(scaled_width, scaled_height) // 2 + 28
        ring_pulse = 1 + (math.sin(tick * 8) * 0.06 if self.state == "speaking" else 0)
        ring_width = 2 if self.state == "idle" else 4
        pygame.draw.circle(self.screen, glow_color, avatar_rect.center, int(ring_radius * ring_pulse), ring_width)

        if self._blink_amount(tick) > 0:
            self._draw_blink(avatar_rect, tick)

    def _draw_subtitle(self, style: dict[str, object]) -> None:
        text_box = pygame.Surface((self.width - 160, 92), pygame.SRCALPHA)
        text_box.fill((10, 10, 10, 190))
        box_rect = text_box.get_rect(center=(self.width // 2, self.height - 82))
        self.screen.blit(text_box, box_rect)

        subtitle_text = self._typed_subtitle()
        subtitle = self.subtitle_font.render(subtitle_text, True, (245, 245, 245))
        self.screen.blit(subtitle, subtitle.get_rect(center=box_rect.center))

        indicator = self.status_font.render(str(style["emoji"]), True, tuple(style["color"]))
        self.screen.blit(indicator, indicator.get_rect(midleft=(box_rect.left + 20, box_rect.centery)))

    def _draw_hint(self) -> None:
        hint = "F: toggle fullscreen   Esc: close"
        hint_surface = self.hint_font.render(hint, True, (170, 170, 170))
        hint_rect = hint_surface.get_rect(bottomright=(self.width - 20, self.height - 16))
        self.screen.blit(hint_surface, hint_rect)

    def _load_avatar(self, avatar_path: Path) -> pygame.Surface:
        if avatar_path.exists():
            return pygame.image.load(str(avatar_path)).convert_alpha()

        fallback = pygame.Surface((420, 420), pygame.SRCALPHA)
        pygame.draw.circle(fallback, (40, 40, 40), (210, 210), 180)
        pygame.draw.circle(fallback, (230, 230, 230), (210, 165), 76)
        pygame.draw.rect(fallback, (230, 230, 230), pygame.Rect(138, 240, 144, 98), border_radius=36)
        return fallback

    def _typed_subtitle(self) -> str:
        elapsed = max(0, pygame.time.get_ticks() - self.subtitle_changed_at)
        chars_per_second = 36 if self.state == "speaking" else 60
        visible_chars = max(1, int((elapsed / 1000) * chars_per_second))
        if self.state in {"speaking", "greeting"}:
            return self.subtitle[:visible_chars]
        return self.subtitle

    def _blink_amount(self, tick: float) -> float:
        cycle = tick % 4.2
        if 3.75 <= cycle <= 3.93:
            midpoint = 3.84
            distance = abs(cycle - midpoint)
            return max(0.0, 1 - (distance / 0.09))
        return 0.0

    def _draw_blink(self, avatar_rect: pygame.Rect, tick: float) -> None:
        blink = self._blink_amount(tick)
        if blink <= 0:
            return

        eye_y = avatar_rect.top + int(avatar_rect.height * 0.34)
        eye_width = int(avatar_rect.width * 0.18)
        eye_height = max(6, int(avatar_rect.height * 0.09 * blink))
        eye_spacing = int(avatar_rect.width * 0.18)
        for direction in (-1, 1):
            center_x = avatar_rect.centerx + direction * eye_spacing
            eyelid_rect = pygame.Rect(0, 0, eye_width, eye_height)
            eyelid_rect.center = (center_x, eye_y)
            pygame.draw.ellipse(self.screen, (8, 16, 32), eyelid_rect)
