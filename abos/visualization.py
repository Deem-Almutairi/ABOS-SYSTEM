"""Futuristic AI operational dashboard — pygame visualization."""

from __future__ import annotations

import math
import time

import pygame

from abos import config
from abos.simulation import SimulationState


def _lerp_color(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def _heat_color(v: float) -> tuple[int, int, int]:
    if v < 0.3:
        return _lerp_color(config.COLOR_HEAT_LOW, config.COLOR_HEAT_MED, v / 0.3)
    return _lerp_color(config.COLOR_HEAT_MED, config.COLOR_HEAT_HIGH, (v - 0.3) / 0.7)


class Dashboard:
    def __init__(self) -> None:
        if not pygame.get_init():
            pygame.init()
        if not pygame.font.get_init():
            pygame.font.init()

        flags = 0
        self.screen = pygame.display.set_mode(
            (config.SCREEN_WIDTH, config.SCREEN_HEIGHT), flags
        )
        pygame.display.set_caption(config.TITLE)
        allowed = [pygame.QUIT, pygame.KEYDOWN]
        if hasattr(pygame, "WINDOWCLOSE"):
            allowed.append(pygame.WINDOWCLOSE)
        pygame.event.set_allowed(allowed)
        pygame.event.pump()
        pygame.display.flip()
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 13)
        self.font_sm = pygame.font.SysFont("consolas", 11)
        self.font_lg = pygame.font.SysFont("consolas", 16, bold=True)
        self.font_title = pygame.font.SysFont("consolas", 20, bold=True)
        self._pulse = 0.0
        self._start_time = time.time()

    def show_loading(self, message: str) -> None:
        """Display a splash screen while simulation data loads."""
        self.screen.fill(config.COLOR_BG)
        title = self.font_title.render("ABOS", True, config.COLOR_ACCENT)
        self.screen.blit(
            title,
            title.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 - 30)),
        )
        msg = self.font.render(message, True, config.COLOR_TEXT_DIM)
        self.screen.blit(
            msg,
            msg.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 + 10)),
        )
        pygame.display.flip()
        pygame.event.pump()

    def handle_events(self, state: SimulationState) -> bool:
        from abos.scenarios import ScenarioType

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_1:
                    state.trigger_scenario(ScenarioType.EVACUATION)
                if event.key == pygame.K_2:
                    state.trigger_scenario(ScenarioType.GATE_OVERCROWD)
                if event.key == pygame.K_3:
                    state.trigger_scenario(ScenarioType.HOSPITAL_OVERLOAD)
                if event.key == pygame.K_4:
                    state.trigger_scenario(ScenarioType.CROWD_SURGE)
                if event.key == pygame.K_0:
                    state.scenarios.clear()
        return True

    def draw(self, state: SimulationState) -> None:
        self._pulse = (math.sin(state.frame * 0.08) + 1) / 2
        self.screen.fill(config.COLOR_BG)
        self._draw_simulation(state)
        self._draw_sidebar(state)
        self._draw_header(state)
        pygame.display.flip()

    def _draw_header(self, state: SimulationState) -> None:
        status_color = config.COLOR_OK
        if "EMERGENCY" in state.system_status or "SURGE" in state.system_status:
            status_color = config.COLOR_CRITICAL
        elif state.system_status != "NOMINAL":
            status_color = config.COLOR_WARN

        title = self.font_title.render("ABOS  |  AI OPERATIONAL CONTROL", True, config.COLOR_ACCENT)
        self.screen.blit(title, (14, 8))

        mode = config.FACILITY_MODE.upper()
        sub = self.font.render(f"Facility: {mode}  |  Agents: {len(state.agents)}  |  Frame {state.frame}", True, config.COLOR_TEXT_DIM)
        self.screen.blit(sub, (14, 32))

        status_surf = self.font_lg.render(state.system_status, True, status_color)
        self.screen.blit(status_surf, (config.SIM_WIDTH - status_surf.get_width() - 20, 10))

    def _draw_simulation(self, state: SimulationState) -> None:
        sim_rect = pygame.Rect(0, config.HEADER_HEIGHT, config.SIM_WIDTH, config.SIM_HEIGHT)
        pygame.draw.rect(self.screen, config.COLOR_FLOOR, sim_rect)

        # Walls
        cs = config.CELL_SIZE
        for cy in range(state.env.rows):
            for cx in range(state.env.cols):
                if not state.env.grid[cy][cx]:
                    r = pygame.Rect(cx * cs, config.HEADER_HEIGHT + cy * cs, cs, cs)
                    pygame.draw.rect(self.screen, config.COLOR_WALL, r)

        # Zone fills + labels
        forecast_map = {f.zone.id: f for f in state.forecasts}
        for zone in state.env.zones:
            f = forecast_map.get(zone.id)
            base = config.ZONE_COLORS.get(zone.id, (30, 40, 55))
            alpha = 40 + int(zone.density * 80)
            if f and f.congested:
                base = (80, 30, 35)
            elif f and f.predicted:
                base = (70, 55, 25)

            zr = pygame.Rect(
                int(zone.x), int(config.HEADER_HEIGHT + zone.y),
                int(zone.width), int(zone.height),
            )
            surf = pygame.Surface((zr.width, zr.height), pygame.SRCALPHA)
            surf.fill((*base, min(160, alpha)))
            self.screen.blit(surf, zr.topleft)

            border_color = config.COLOR_PANEL_BORDER
            if f and f.congested:
                border_color = config.COLOR_ALERT
            elif f and f.predicted:
                border_color = config.COLOR_WARN
            pygame.draw.rect(self.screen, border_color, zr, 1)

            label = self.font_sm.render(zone.label, True, config.COLOR_TEXT)
            self.screen.blit(label, (zr.x + 6, zr.y + 4))

            if f and f.predicted and not f.congested:
                pygame.draw.rect(self.screen, config.COLOR_WARN, zr, 2)

        # Heatmap overlay
        if state.heatmap:
            rows, cols = len(state.heatmap), len(state.heatmap[0])
            hw = config.SIM_WIDTH / cols
            hh = config.SIM_HEIGHT / rows
            for r in range(rows):
                for c in range(cols):
                    v = state.heatmap[r][c]
                    if v < 0.05:
                        continue
                    hr = pygame.Rect(
                        int(c * hw), int(config.HEADER_HEIGHT + r * hh),
                        int(hw) + 1, int(hh) + 1,
                    )
                    col = _heat_color(v)
                    hs = pygame.Surface((hr.width, hr.height), pygame.SRCALPHA)
                    hs.fill((*col, int(v * 140)))
                    self.screen.blit(hs, hr.topleft)

        # Adaptive routing paths
        for agent in state.agents:
            if agent.rerouted and len(agent.path) > 1:
                pts = [
                    (int(p[0]), int(config.HEADER_HEIGHT + p[1]))
                    for p in agent.path[agent.path_index : agent.path_index + 8]
                ]
                if len(pts) >= 2:
                    pygame.draw.lines(self.screen, config.COLOR_ACCENT_DIM, False, pts, 1)

        # Agents
        for agent in state.agents:
            color = config.COLOR_AGENT.get(agent.behavior.value, config.COLOR_AGENT["compliant"])
            if agent.rerouted:
                color = config.COLOR_REROUTE
            if agent.panic:
                color = config.COLOR_CRITICAL
            pygame.draw.circle(
                self.screen, color,
                (int(agent.x), int(config.HEADER_HEIGHT + agent.y)),
                config.AGENT_RADIUS,
            )

        # Zone risk badges on congested areas
        for f in state.forecasts:
            if f.congested or f.predicted:
                zx, zy = f.zone.center
                badge = f.risk_level[:3]
                bs = self.font_sm.render(badge, True, config.COLOR_ALERT if f.congested else config.COLOR_WARN)
                self.screen.blit(bs, (int(zx) - 10, int(config.HEADER_HEIGHT + zy) - 6))

        # Sim border
        pygame.draw.rect(self.screen, config.COLOR_PANEL_BORDER, sim_rect, 2)

    def _draw_sidebar(self, state: SimulationState) -> None:
        sx = config.SIM_WIDTH
        panel = pygame.Rect(sx, 0, config.SIDEBAR_WIDTH, config.SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, config.COLOR_PANEL, panel)
        pygame.draw.line(self.screen, config.COLOR_ACCENT, (sx, 0), (sx, config.SCREEN_HEIGHT), 2)

        y = 58
        y = self._section_title("LIVE METRICS", sx + 14, y)

        uptime = int(time.time() - self._start_time)
        metrics = [
            ("Active agents", str(len(state.agents))),
            ("Congested zones", str(state.congested_count)),
            ("Predicted zones", str(state.predicted_count)),
            ("Avg risk score", f"{state.avg_risk:.0%}"),
            ("AI confidence", f"{state.avg_confidence:.0%}"),
            ("Reroutes", str(state.optimizer.reroute_count)),
            ("Paths computed", str(state.optimizer.paths_computed)),
            ("Uptime", f"{uptime // 60:02d}:{uptime % 60:02d}"),
        ]
        for label, value in metrics:
            y = self._metric_row(label, value, sx + 14, y)
        y += 10

        y = self._section_title("ZONE RISK", sx + 14, y)
        sorted_f = sorted(state.forecasts, key=lambda f: f.risk_score, reverse=True)[:6]
        for f in sorted_f:
            bar_w = int((config.SIDEBAR_WIDTH - 40) * f.risk_score)
            risk_col = config.COLOR_OK
            if f.risk_score > 0.65:
                risk_col = config.COLOR_ALERT
            elif f.risk_score > 0.4:
                risk_col = config.COLOR_WARN
            name = self.font_sm.render(f.zone.label[:18], True, config.COLOR_TEXT_DIM)
            self.screen.blit(name, (sx + 14, y))
            y += 14
            pygame.draw.rect(self.screen, (30, 40, 55), (sx + 14, y, config.SIDEBAR_WIDTH - 40, 6))
            pygame.draw.rect(self.screen, risk_col, (sx + 14, y, bar_w, 6))
            y += 16

        y += 6
        y = self._section_title("OPERATIONAL ALERTS", sx + 14, y)
        alerts = state.alerts[-6:] or state.predictor.alerts[-6:] or ["No active alerts"]
        for msg in reversed(alerts):
            col = config.COLOR_TEXT
            if "Predicted" in msg:
                col = config.COLOR_WARN
            if "ACTIVE" in msg or "EMERGENCY" in msg:
                col = config.COLOR_ALERT
            wrapped = msg[:42]
            surf = self.font_sm.render(wrapped, True, col)
            self.screen.blit(surf, (sx + 14, y))
            y += 16
            if y > config.SCREEN_HEIGHT - 120:
                break

        y = config.SCREEN_HEIGHT - 110
        y = self._section_title("SCENARIOS [keys]", sx + 14, y)
        hints = [
            "1 — Evacuation",
            "2 — Gate overcrowd",
            "3 — Facility overload",
            "4 — Crowd surge",
            "0 — Clear scenario",
        ]
        for h in hints:
            s = self.font_sm.render(h, True, config.COLOR_TEXT_DIM)
            self.screen.blit(s, (sx + 14, y))
            y += 14

        if state.scenarios.active.value != "none":
            sc = self.font.render(state.scenarios.label, True, config.COLOR_ALERT)
            self.screen.blit(sc, (sx + 14, y + 4))

    def _section_title(self, text: str, x: int, y: int) -> int:
        surf = self.font_lg.render(text, True, config.COLOR_ACCENT)
        self.screen.blit(surf, (x, y))
        pygame.draw.line(self.screen, config.COLOR_PANEL_BORDER, (x, y + 20), (x + config.SIDEBAR_WIDTH - 28, y + 20), 1)
        return y + 26

    def _metric_row(self, label: str, value: str, x: int, y: int) -> int:
        ls = self.font_sm.render(label, True, config.COLOR_TEXT_DIM)
        vs = self.font.render(value, True, config.COLOR_TEXT)
        self.screen.blit(ls, (x, y))
        self.screen.blit(vs, (x + config.SIDEBAR_WIDTH - 40 - vs.get_width(), y))
        return y + 20

    def tick(self) -> None:
        self.clock.tick(config.FPS)

    def quit(self) -> None:
        pygame.quit()
