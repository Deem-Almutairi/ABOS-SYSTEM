"""Emergency and overload scenario simulation."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

from abos import config
from abos.agents import Agent, BehaviorType
from abos.environment import FacilityEnvironment
from abos.optimization import AdaptiveOptimizer


class ScenarioType(str, Enum):
    NONE = "none"
    EVACUATION = "evacuation"
    GATE_OVERCROWD = "gate_overcrowd"
    HOSPITAL_OVERLOAD = "hospital_overload"
    CROWD_SURGE = "crowd_surge"


@dataclass
class ScenarioManager:
    active: ScenarioType = ScenarioType.NONE
    frames_remaining: int = 0
    label: str = "Normal Operations"
    surge_spawned: bool = False

    def trigger(self, scenario: ScenarioType) -> str:
        self.active = scenario
        self.frames_remaining = config.SCENARIO_DURATION
        self.surge_spawned = False
        labels = {
            ScenarioType.EVACUATION: "EMERGENCY EVACUATION",
            ScenarioType.GATE_OVERCROWD: "GATE OVERCROWDING",
            ScenarioType.HOSPITAL_OVERLOAD: "FACILITY OVERLOAD",
            ScenarioType.CROWD_SURGE: "CROWD SURGE EVENT",
        }
        self.label = labels.get(scenario, "Normal Operations")
        return self.label

    def clear(self) -> None:
        self.active = ScenarioType.NONE
        self.frames_remaining = 0
        self.label = "Normal Operations"

    def update(
        self,
        env: FacilityEnvironment,
        agents: list[Agent],
        optimizer: AdaptiveOptimizer,
    ) -> list[Agent]:
        if self.active == ScenarioType.NONE:
            return agents

        self.frames_remaining -= 1
        if self.frames_remaining <= 0:
            self.clear()
            for a in agents:
                a.panic = False
            return agents

        if self.active == ScenarioType.EVACUATION:
            optimizer.force_evacuation_routes(env, agents)

        elif self.active == ScenarioType.GATE_OVERCROWD:
            gate = env.zone_by_id("gate_b") or env.gate_zones()[0] if env.gate_zones() else None
            if gate:
                for _ in range(3):
                    agents.append(self._spawn_at_zone(env, gate, BehaviorType.FOLLOWER))

        elif self.active == ScenarioType.HOSPITAL_OVERLOAD:
            triage = env.zone_by_id("security")
            if triage:
                triage.capacity *= 0.6
            lounge = env.zone_by_id("waiting_lounge")
            if lounge and not self.surge_spawned:
                for _ in range(15):
                    agents.append(self._spawn_at_zone(env, lounge, BehaviorType.COMPLIANT))
                self.surge_spawned = True

        elif self.active == ScenarioType.CROWD_SURGE:
            entrance = env.zone_by_id("main_entrance")
            if entrance and not self.surge_spawned:
                for _ in range(config.SURGE_SPAWN_COUNT):
                    agents.append(self._spawn_at_zone(env, entrance, BehaviorType.IMPATIENT))
                self.surge_spawned = True

        return agents

    def _spawn_at_zone(self, env: FacilityEnvironment, zone, behavior: BehaviorType) -> Agent:
        x, y = zone.center
        x += random.uniform(-zone.width * 0.2, zone.width * 0.2)
        y += random.uniform(-zone.height * 0.2, zone.height * 0.2)
        journey = env.journey_order()
        return Agent(
            x=x, y=y,
            behavior=behavior,
            journey=list(journey),
            journey_index=min(2, len(journey) - 1),
        )
