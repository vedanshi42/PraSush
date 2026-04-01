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
        self.active = False

    def set_active(self):
        self.active = True

    def set_idle(self):
        self.active = False
        self.subtitle = ""

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
        self.screen.fill((0, 0, 0))
        if self.active:
            self._draw_avatar()
            self._draw_subtitle()
        pygame.display.flip()
        self.clock.tick(30)

    def _draw_avatar(self):
        center_x = self.width // 2
        center_y = self.height // 2 - 80
        radius = min(self.width, self.height) // 8
        pulse = int(8 * math.sin(pygame.time.get_ticks() / 250))
        head_color = (24, 24, 24)
        glow_color = (80, 80, 220)

        pygame.draw.circle(self.screen, glow_color, (center_x, center_y), radius + 40, 2)
        pygame.draw.circle(self.screen, head_color, (center_x, center_y), radius)
        pygame.draw.circle(self.screen, (50, 50, 120), (center_x - radius - 20, center_y - 10), radius // 2)
        pygame.draw.circle(self.screen, (50, 50, 120), (center_x + radius + 20, center_y - 10), radius // 2)

        eye_y = center_y - radius // 6
        eye_x_offset = radius // 2
        pygame.draw.ellipse(self.screen, (245, 245, 245), (center_x - eye_x_offset - 24, eye_y - 18, 48, 36))
        pygame.draw.ellipse(self.screen, (245, 245, 245), (center_x + eye_x_offset - 24, eye_y - 18, 48, 36))
        pygame.draw.circle(self.screen, (32, 32, 32), (center_x - eye_x_offset, eye_y), 12 + pulse // 4)
        pygame.draw.circle(self.screen, (32, 32, 32), (center_x + eye_x_offset, eye_y), 12 + pulse // 4)

        mouth_width = radius // 2
        mouth_rect = pygame.Rect(center_x - mouth_width, center_y + radius // 5, 2 * mouth_width, 20)
        pygame.draw.arc(self.screen, (200, 200, 255), mouth_rect, math.pi / 8, math.pi - math.pi / 8, 4)

        glow_surface = pygame.Surface((radius * 2 + 120, radius * 2 + 120), pygame.SRCALPHA)
        pygame.draw.circle(glow_surface, (50, 60, 180, 60), (glow_surface.get_width() // 2, glow_surface.get_height() // 2), radius + 50)
        self.screen.blit(glow_surface, (center_x - glow_surface.get_width() // 2, center_y - glow_surface.get_height() // 2), special_flags=pygame.BLEND_RGBA_ADD)

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
