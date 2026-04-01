import sys
import math
import pygame


class DisplayManager:
    def __init__(self):
        pygame.init()
        self.flags = pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF
        self.screen = pygame.display.set_mode((0, 0), self.flags)
        self.width, self.height = self.screen.get_size()
        pygame.display.set_caption("PraSush")
        self.font = pygame.font.Font(None, 56)
        self.small_font = pygame.font.Font(None, 32)
        self.clock = pygame.time.Clock()
        self.subtitle = ""
        self.visible = False
        self.active = False
        self.environment_summary = "Waiting for wake word..."

    def set_active(self):
        self.visible = True
        self.active = True

    def set_idle(self):
        self.visible = True
        self.active = False

    def hide(self):
        self.visible = False
        self.active = False
        self.subtitle = ""

    def set_environment_summary(self, text):
        self.environment_summary = text

    def set_subtitle(self, text):
        self.subtitle = text

    def pump_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.close()

    def render(self):
        self.screen.fill((10, 10, 18))
        if self.visible:
            self._draw_avatar()
            self._draw_status()
            self._draw_subtitle()
        pygame.display.flip()
        self.clock.tick(30)

    def _draw_avatar(self):
        center_x = self.width // 2
        center_y = self.height // 2 - 80
        radius = min(self.width, self.height) // 8
        tick = pygame.time.get_ticks() / 250
        pulse = int(10 * math.sin(tick))
        active_level = 255 if self.active else 140
        glow_alpha = 120 if self.active else 60
        glow_color = (80, 160, 240)
        core_color = (28, 35, 80)
        accent_color = (90, 170, 255)
        rim_color = (70, 100, 180)

        halo = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
        pygame.draw.circle(halo, (60, 100, 220, glow_alpha), (halo.get_width() // 2, halo.get_height() // 2), radius + 60)
        self.screen.blit(halo, (center_x - halo.get_width() // 2, center_y - halo.get_height() // 2), special_flags=pygame.BLEND_RGBA_ADD)

        pygame.draw.circle(self.screen, rim_color, (center_x, center_y), radius + 30, 8)
        pygame.draw.ellipse(self.screen, core_color, (center_x - radius, center_y - radius, radius * 2, radius * 2 + 24))
        pygame.draw.ellipse(self.screen, (30, 40, 90), (center_x - radius + 10, center_y - radius + 10, radius * 2 - 20, radius * 2 + 4))

        visor_rect = pygame.Rect(center_x - radius + 8, center_y - radius // 2, radius * 2 - 16, radius // 2)
        pygame.draw.ellipse(self.screen, (20, 100, 170), visor_rect)
        pygame.draw.ellipse(self.screen, accent_color, visor_rect.inflate(-12, -10), 2)

        for offset in (-1, 1):
            eye_center = (center_x + offset * (radius // 2 + 14), center_y - 12)
            pygame.draw.ellipse(self.screen, (240, 245, 255), (*eye_center, 30, 18))
            pupil_color = (180, 230, 255) if self.active else (120, 160, 200)
            pygame.draw.circle(self.screen, pupil_color, eye_center, 9 + (pulse // 8 if self.active else 0))
            pygame.draw.circle(self.screen, (18, 28, 60), eye_center, 4)

        brow_y = center_y - radius // 2
        pygame.draw.arc(self.screen, accent_color, (center_x - radius + 20, brow_y - 12, radius * 2 - 40, 32), math.pi, 2 * math.pi, 3)

        mouth_rect = pygame.Rect(center_x - radius // 3, center_y + radius // 4, radius * 2 // 3, 18)
        smile = (200, 230, 255) if self.active else (120, 160, 190)
        pygame.draw.arc(self.screen, smile, mouth_rect, math.pi / 10, math.pi - math.pi / 10, 4)

        for angle in range(0, 360, 45):
            radians = math.radians(angle + pulse)
            orbit_x = center_x + int(math.cos(radians) * (radius + 90))
            orbit_y = center_y + int(math.sin(radians) * (radius + 90))
            dot_color = (120, 190, 255, 200) if self.active else (80, 120, 180, 140)
            pygame.draw.circle(self.screen, dot_color, (orbit_x, orbit_y), 6)

        for i in range(4):
            offset = (i - 1.5) * 40
            pygame.draw.line(
                self.screen,
                accent_color,
                (center_x + offset, center_y + radius + 12),
                (center_x + offset, center_y + radius + 42),
                4,
            )

        core_glow = pygame.Surface((radius * 2 + 80, radius * 2 + 80), pygame.SRCALPHA)
        pygame.draw.circle(core_glow, (80, 150, 255, 50 if self.active else 25), (core_glow.get_width() // 2, core_glow.get_height() // 2), radius + 40)
        self.screen.blit(core_glow, (center_x - core_glow.get_width() // 2, center_y - core_glow.get_height() // 2), special_flags=pygame.BLEND_RGBA_ADD)

    def _draw_status(self):
        status = "AWAKE" if self.active else "IDLE"
        detail = "Observing environment and learning from signals." if not self.active else "Listening and adapting to your request."
        status_text = f"{status} • {detail}"
        text_surface = self.small_font.render(status_text, True, (200, 220, 255))
        text_rect = text_surface.get_rect(center=(self.width // 2, 80))
        self.screen.blit(text_surface, text_rect)

        summary_text = self.small_font.render(self.environment_summary, True, (180, 200, 230))
        summary_rect = summary_text.get_rect(center=(self.width // 2, 120))
        self.screen.blit(summary_text, summary_rect)

    def _draw_subtitle(self):
        if not self.subtitle:
            return
        text_surface = self.small_font.render(self.subtitle, True, (230, 230, 230))
        text_rect = text_surface.get_rect(center=(self.width // 2, self.height - 80))
        background = pygame.Surface((text_rect.width + 24, text_rect.height + 18), pygame.SRCALPHA)
        background.fill((0, 0, 0, 180))
        background_rect = background.get_rect(center=text_rect.center)
        self.screen.blit(background, background_rect)
        self.screen.blit(text_surface, text_rect)

    def close(self):
        pygame.quit()
        sys.exit(0)
