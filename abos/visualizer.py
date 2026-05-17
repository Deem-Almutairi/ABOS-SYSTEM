"""Pygame real-time visualization for ABOS."""

from __future__ import annotations

import pygame

from abos import config
from abos.response import Warning
from abos.simulation import SimulationState


def _density_color(density: float, congested: bool) -> tuple[int, int, int]:
    if congested or density >= config.DENSITY_HIGH:
        return config.COLOR_ZONE_CRITICAL
    if density >= config.DENSITY_MEDIUM:
        return config.COLOR_ZONE_HIGH
    if density >= config.DENSITY_LOW:
        return config.COLOR_ZONE_MED
    if density > 0.05:
        return config.COLOR_ZONE_LOW
    return config.COLOR_ZONE_EMPTY


class Visualizer:
    def __init__(self, width: int, height: int) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption(config.TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 14)
        self.font_large = pygame.font.SysFont("consolas", 18, bold=True)
        self.width = width
        self.height = height

    def handle_events(self) -> bool:
        """Return False to quit."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
        return True

    def draw(
        self,
        state: SimulationState,
        warnings: list[Warning],
    ) -> None:
        self.screen.fill(config.COLOR_BG)
        forecast_map = {id(f.zone): f for f in state.forecasts}

        for zone in state.grid.zones:
            f = forecast_map.get(id(zone))
            congested = f.congested if f else False
            predicted = f.predicted_congestion if f else False
            color = _density_color(zone.density, congested)

            rect = pygame.Rect(int(zone.x), int(zone.y), int(zone.width), int(zone.height))
            surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            alpha = 80 + int(zone.density * 120)
            surf.fill((*color, min(200, alpha)))
            self.screen.blit(surf, rect.topleft)
            pygame.draw.rect(self.screen, (60, 68, 78), rect, 1)

            if predicted and not congested:
                pygame.draw.rect(self.screen, (255, 200, 80), rect, 2)

        for agent in state.agents:
            color = config.REROUTE_COLOR if agent.rerouted else config.AGENT_COLOR
            pygame.draw.circle(
                self.screen,
                color,
                (int(agent.x), int(agent.y)),
                config.AGENT_RADIUS,
            )

        for warning in warnings:
            zx, zy = warning.zone.center
            label = self.font.render("!", True, config.COLOR_WARNING)
            self.screen.blit(label, (int(zx) - 4, int(zy) - 8))

        self._draw_hud(state)
        pygame.display.flip()

    def _draw_hud(self, state: SimulationState) -> None:
        lines = [
            f"ABOS v0.1  |  Frame {state.frame}",
            f"Agents: {len(state.agents)}  |  Reroutes: {state.responder.reroute_count}",
            f"Congested zones: {state.congested_zone_count}  |  Predicted: {state.predicted_zone_count}",
        ]
        if state.warnings:
            lines.append(f"Alert: {state.warnings[0]}")

        y = 10
        for i, line in enumerate(lines):
            font = self.font_large if i == 0 else self.font
            surf = font.render(line, True, config.COLOR_TEXT)
            self.screen.blit(surf, (12, y))
            y += surf.get_height() + 4

        legend = "Green→Yellow→Red = density  |  Orange outline = predicted  |  ESC quit"
        surf = self.font.render(legend, True, (140, 150, 165))
        self.screen.blit(surf, (12, self.height - 24))

    def tick(self) -> None:
        self.clock.tick(config.FPS)

    def quit(self) -> None:
        pygame.quit()
