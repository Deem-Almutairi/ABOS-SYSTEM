"""Adaptive responses: warnings and agent rerouting."""

from __future__ import annotations

from dataclasses import dataclass, field

from abos import config
from abos.agents import Agent
from abos.prediction import ZoneForecast
from abos.zones import Zone, ZoneGrid


@dataclass
class Warning:
    zone: Zone
    message: str
    frames_left: int


@dataclass
class AdaptiveResponder:
    warnings: list[Warning] = field(default_factory=list)
    reroute_count: int = 0

    def process(
        self,
        forecasts: list[ZoneForecast],
        agents: list[Agent],
        grid: ZoneGrid,
    ) -> list[str]:
        """Apply reroutes and emit active warning messages."""
        messages: list[str] = []
        hot_zones = [f for f in forecasts if f.congested or f.predicted_congestion]

        for forecast in hot_zones:
            if forecast.congested:
                msg = f"CONGESTION zone ({forecast.zone.col},{forecast.zone.row})"
            else:
                msg = f"PREDICTED congestion zone ({forecast.zone.col},{forecast.zone.row})"
            messages.append(msg)
            self._add_warning(forecast.zone, msg)

        for agent in agents:
            zone = grid.zone_at(agent.x, agent.y)
            if zone is None:
                continue

            target_zone = grid.zone_at(agent.target_x, agent.target_y)
            needs_reroute = False

            if target_zone:
                for f in hot_zones:
                    if f.zone is target_zone and (f.congested or f.predicted_congestion):
                        needs_reroute = True
                        break

            if needs_reroute or (
                zone
                and any(f.zone is zone and f.congested for f in hot_zones)
            ):
                alt = grid.sparsest_zone(exclude=zone)
                tx, ty = alt.center
                agent.set_target(tx, ty)
                self.reroute_count += 1
            elif agent.rerouted and zone and zone.density < config.DENSITY_LOW:
                agent.clear_reroute()

        self._tick_warnings()
        return [w.message for w in self.warnings]

    def _add_warning(self, zone: Zone, message: str) -> None:
        for w in self.warnings:
            if w.zone is zone and w.frames_left > 0:
                w.frames_left = config.WARNING_COOLDOWN
                w.message = message
                return
        self.warnings.append(Warning(zone=zone, message=message, frames_left=config.WARNING_COOLDOWN))

    def _tick_warnings(self) -> None:
        for w in self.warnings:
            w.frames_left -= 1
        self.warnings = [w for w in self.warnings if w.frames_left > 0]
