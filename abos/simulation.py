"""Core ABOS simulation loop (logic only, no rendering)."""

from __future__ import annotations

from dataclasses import dataclass, field

from abos.agents import Agent, spawn_agents
from abos.prediction import CongestionPredictor, ZoneForecast
from abos.response import AdaptiveResponder
from abos.zones import ZoneGrid


@dataclass
class SimulationState:
    agents: list[Agent]
    grid: ZoneGrid
    width: int
    height: int
    predictor: CongestionPredictor = field(default_factory=CongestionPredictor)
    responder: AdaptiveResponder = field(default_factory=AdaptiveResponder)
    frame: int = 0
    forecasts: list[ZoneForecast] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def create(cls, width: int, height: int, num_agents: int) -> SimulationState:
        return cls(
            agents=spawn_agents(num_agents, width, height),
            grid=ZoneGrid.from_screen(width, height),
            width=width,
            height=height,
        )

    def step(self) -> None:
        positions = [(a.x, a.y) for a in self.agents]
        self.grid.update_counts(positions)

        self.forecasts = self.predictor.update(self.grid)
        self.warnings = self.responder.process(self.forecasts, self.agents, self.grid)

        for agent in self.agents:
            agent.update(self.width, self.height)

        self.frame += 1

    @property
    def congested_zone_count(self) -> int:
        return sum(1 for f in self.forecasts if f.congested)

    @property
    def predicted_zone_count(self) -> int:
        return sum(1 for f in self.forecasts if f.predicted_congestion and not f.congested)
