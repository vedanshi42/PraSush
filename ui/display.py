from __future__ import annotations

import math
import sys
from pathlib import Path

import pygame

from config import AVATAR_PATH, PROJECT_NAME, WINDOW_HEIGHT, WINDOW_WIDTH

STATE_STYLES = {
    "idle": {"label": "Idle", "zoom": 0.99, "alpha": 210},
    "listening": {"label": "Listening", "zoom": 1.01, "alpha": 255},
    "thinking": {"label": "Thinking", "zoom": 1.015, "alpha": 248},
    "speaking": {"label": "Speaking", "zoom": 1.02, "alpha": 255},
    "greeting": {"label": "Greeting", "zoom": 1.025, "alpha": 255},
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
        self.status_font = pygame.font.Font(None, 24)
        self.subtitle_font = pygame.font.Font(None, 34)
        self.avatar_surface = self._load_avatar(avatar_path)
        self.state = "idle"
        self.status_text = "Waiting for wake word"
        self.subtitle = "Say hi to begin."
        self.subtitle_changed_at = pygame.time.get_ticks()

    def set_state(self, state: str, status_text: str, subtitle: str) -> None:
        if state not in STATE_STYLES:
            raise ValueError(f"Unknown UI state: {state}")
        self.state = state
        self.status_text = status_text
        self.subtitle = subtitle
        self.subtitle_changed_at = pygame.time.get_ticks()
        self.render()

    def pump_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.close()
                if event.key == pygame.K_f:
                    self.toggle_fullscreen()
            if event.type == pygame.VIDEORESIZE and not self.is_fullscreen:
                self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE | pygame.DOUBLEBUF)
                self.width, self.height = self.screen.get_size()

    def render(self) -> None:
        tick = pygame.time.get_ticks() / 1000
        style = STATE_STYLES[self.state]
        pulse = 1 + math.sin(tick * 2.0) * 0.012
        zoom = style["zoom"] * pulse

        self.screen.fill((0, 0, 0))
        self._draw_avatar(zoom, tick, int(style["alpha"]))
        self._draw_status(style)
        self._draw_subtitle()
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

    def _draw_status(self, style: dict[str, object]) -> None:
        if self.state == "idle":
            return
        status = self.status_font.render(self.status_text, True, (165, 180, 205))
        self.screen.blit(status, status.get_rect(center=(self.width // 2, 36)))

    def _draw_avatar(self, zoom: float, tick: float, alpha: int) -> None:
        base_width = min(int(self.width * 0.34), 520)
        aspect_ratio = self.avatar_surface.get_height() / max(self.avatar_surface.get_width(), 1)
        scaled_width = max(80, int(base_width * zoom))
        scaled_height = max(80, int(scaled_width * aspect_ratio))
        avatar = pygame.transform.smoothscale(self.avatar_surface, (scaled_width, scaled_height))
        avatar = pygame.transform.rotozoom(avatar, self._avatar_rotation(tick), 1.0)
        avatar.set_alpha(alpha)
        shadow = pygame.Surface((scaled_width + 80, scaled_height + 80), pygame.SRCALPHA)
        pygame.draw.ellipse(
            shadow,
            (40, 90, 160, 48 if self.state != "idle" else 20),
            shadow.get_rect().inflate(-50, -scaled_height // 2),
        )
        avatar_y = self.height // 2 + math.sin(tick * 2.0) * 5
        shadow_rect = shadow.get_rect(center=(self.width // 2, avatar_y + scaled_height // 2 + 16))
        avatar_rect = avatar.get_rect(center=(self.width // 2, avatar_y))
        self.screen.blit(shadow, shadow_rect)
        self.screen.blit(avatar, avatar_rect)

    def _draw_subtitle(self) -> None:
        subtitle_text = self._typed_subtitle()
        shadow = self.subtitle_font.render(subtitle_text, True, (0, 0, 0))
        subtitle = self.subtitle_font.render(subtitle_text, True, (245, 245, 245))
        center = (self.width // 2, self.height - 52)
        self.screen.blit(shadow, shadow.get_rect(center=(center[0] + 2, center[1] + 2)))
        self.screen.blit(subtitle, subtitle.get_rect(center=center))

    def _load_avatar(self, avatar_path: Path) -> pygame.Surface:
        if avatar_path.exists():
            surface = pygame.image.load(str(avatar_path)).convert_alpha()
            return self._soft_remove_dark_background(surface)

        fallback = pygame.Surface((420, 420), pygame.SRCALPHA)
        pygame.draw.circle(fallback, (230, 230, 230), (210, 210), 150)
        return fallback

    def _typed_subtitle(self) -> str:
        elapsed = max(0, pygame.time.get_ticks() - self.subtitle_changed_at)
        chars_per_second = 36 if self.state == "speaking" else 72
        visible_chars = max(1, int((elapsed / 1000) * chars_per_second))
        if self.state in {"speaking", "greeting"}:
            return self.subtitle[:visible_chars]
        return self.subtitle

    def _soft_remove_dark_background(self, surface: pygame.Surface) -> pygame.Surface:
        cleaned = surface.copy()
        width, height = cleaned.get_size()
        for x in range(width):
            for y in range(height):
                r, g, b, a = cleaned.get_at((x, y))
                brightness = (r + g + b) / 3
                if brightness < 18:
                    cleaned.set_at((x, y), (0, 0, 0, 0))
                elif brightness < 42:
                    cleaned.set_at((x, y), (r, g, b, int(a * 0.35)))
        return cleaned

    def _avatar_rotation(self, tick: float) -> float:
        if self.state == "greeting":
            return math.sin(tick * 3.2) * 2.2
        if self.state == "speaking":
            return math.sin(tick * 4.6) * 0.8
        if self.state == "listening":
            return math.sin(tick * 2.0) * 0.9
        if self.state == "thinking":
            return math.sin(tick * 1.4) * 0.6
        return math.sin(tick * 1.1) * 0.35
