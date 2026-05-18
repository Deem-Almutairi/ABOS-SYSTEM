"""Core ABOS simulation orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field

from abos import config
from abos.agents import Agent, agents_near, spawn_agents
from abos.ai_prediction import CongestionPredictor, ZoneForecast
from abos.environment import FacilityEnvironment
from abos.optimization import AdaptiveOptimizer
from abos.scenarios import ScenarioManager, ScenarioType


@dataclass
class SimulationState:
    env: FacilityEnvironment
    agents: list[Agent]
    predictor: CongestionPredictor = field(default_factory=CongestionPredictor)
    optimizer: AdaptiveOptimizer = field(default_factory=AdaptiveOptimizer)
    scenarios: ScenarioManager = field(default_factory=ScenarioManager)
    frame: int = 0
    forecasts: list[ZoneForecast] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)
    heatmap: list[list[float]] = field(default_factory=list)
    system_status: str = "NOMINAL"

    @classmethod
    def create(cls, num_agents: int | None = None) -> SimulationState:
        env = FacilityEnvironment.build()
        count = num_agents or config.NUM_AGENTS
        agents = spawn_agents(count, env)
        state = cls(env=env, agents=agents)
        # Initial paths assigned gradually via optimizer.bootstrap_routes()
        return state

    def bootstrap_pending_routes(self) -> int:
        """Assign paths for agents that do not have one yet."""
        return self.optimizer.bootstrap_routes(self.env, self.agents)

    def step(self) -> None:
        self.env.update_metrics(self.agents)
        self.heatmap = self.env.cell_density_map(self.agents)

        self.forecasts = self.predictor.update(self.env)
        self.alerts = self.optimizer.process(self.env, self.agents, self.forecasts)

        density_map = {z.id: z.density for z in self.env.zones}
        for agent in self.agents:
            nearby = agents_near(agent, self.agents)
            agent.update(self.env, nearby, density_map)

        self.agents = self.scenarios.update(self.env, self.agents, self.optimizer)
        self._update_status()
        self.frame += 1

    def _update_status(self) -> None:
        if self.scenarios.active != ScenarioType.NONE:
            self.system_status = self.scenarios.label
        elif any(f.congested for f in self.forecasts):
            self.system_status = "CONGESTION DETECTED"
        elif any(f.predicted for f in self.forecasts):
            self.system_status = "PREDICTIVE ALERT"
        else:
            self.system_status = "NOMINAL"

    def trigger_scenario(self, scenario: ScenarioType) -> str:
        return self.scenarios.trigger(scenario)

    @property
    def congested_count(self) -> int:
        return sum(1 for f in self.forecasts if f.congested)

    @property
    def predicted_count(self) -> int:
        return sum(1 for f in self.forecasts if f.predicted and not f.congested)

    @property
    def avg_risk(self) -> float:
        if not self.forecasts:
            return 0.0
        return sum(f.risk_score for f in self.forecasts) / len(self.forecasts)

    @property
    def avg_confidence(self) -> float:
        if not self.forecasts:
            return 0.0
        return sum(f.confidence for f in self.forecasts) / len(self.forecasts)
