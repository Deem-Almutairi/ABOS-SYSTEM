"""Crowd agents with behavioral types and path-following movement."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum

from abos import config
from abos.environment import FacilityEnvironment


class BehaviorType(str, Enum):
    COMPLIANT = "compliant"
    IMPATIENT = "impatient"
    FOLLOWER = "follower"
    PANIC_PRONE = "panic_prone"


@dataclass
class Agent:
    x: float
    y: float
    behavior: BehaviorType = BehaviorType.COMPLIANT
    journey: list[str] = field(default_factory=list)
    journey_index: int = 0
    path: list[tuple[float, float]] = field(default_factory=list)
    path_index: int = 0
    vx: float = 0.0
    vy: float = 0.0
    rerouted: bool = False
    panic: bool = False
    wait_timer: int = 0
    _uid: int = field(default=0, repr=False)

    @property
    def target_zone_id(self) -> str | None:
        if self.journey_index < len(self.journey):
            return self.journey[self.journey_index]
        return None

    @property
    def speed_mult(self) -> float:
        if self.panic:
            return 1.6
        if self.behavior == BehaviorType.IMPATIENT:
            return 1.25
        if self.behavior == BehaviorType.COMPLIANT:
            return 1.0
        if self.behavior == BehaviorType.FOLLOWER:
            return 0.95
        return 1.1

    def set_path(self, waypoints: list[tuple[float, float]], rerouted: bool = False) -> None:
        self.path = waypoints
        self.path_index = 0
        self.rerouted = rerouted

    def advance_journey(self) -> str | None:
        self.journey_index += 1
        self.wait_timer = random.randint(30, 120)
        if self.journey_index < len(self.journey):
            return self.journey[self.journey_index]
        return None

    def update(
        self,
        env: FacilityEnvironment,
        nearby: list[Agent],
        zone_density: dict[str, float],
    ) -> None:
        if self.wait_timer > 0:
            self.wait_timer -= 1
            self.vx *= 0.8
            self.vy *= 0.8
            self.x += self.vx
            self.y += self.vy
            return

        # Panic when local density very high
        zone = env.zone_at(self.x, self.y)
        local_density = zone.density if zone else 0.0
        if self.behavior == BehaviorType.PANIC_PRONE and local_density > 0.75:
            self.panic = True
        elif local_density < 0.4:
            self.panic = False

        target = self._current_waypoint()
        if target is None:
            return

        tx, ty = target
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy) or 1.0

        if dist < 10 and self.path_index < len(self.path) - 1:
            self.path_index += 1
            tx, ty = self._current_waypoint() or (tx, ty)
            dx, dy = tx - self.x, ty - self.y
            dist = math.hypot(dx, dy) or 1.0

        # Crowd avoidance
        avoid_x, avoid_y = 0.0, 0.0
        for other in nearby:
            if other is self:
                continue
            odx, ody = self.x - other.x, self.y - other.y
            od = math.hypot(odx, ody)
            if od < 20 and od > 0.1:
                strength = (20 - od) / 20
                avoid_x += (odx / od) * strength * 1.2
                avoid_y += (ody / od) * strength * 1.2

        # Follower: bias toward crowd direction in same zone
        if self.behavior == BehaviorType.FOLLOWER and nearby:
            avg_vx = sum(a.vx for a in nearby if env.zone_at(a.x, a.y) == zone) / max(1, len(nearby))
            avg_vy = sum(a.vy for a in nearby if env.zone_at(a.x, a.y) == zone) / max(1, len(nearby))
            avoid_x -= avg_vx * 0.15
            avoid_y -= avg_vy * 0.15

        # Avoid high-density zones (impatient / panic)
        if self.behavior in (BehaviorType.IMPATIENT, BehaviorType.PANIC_PRONE) or self.panic:
            for zid, dens in zone_density.items():
                if dens > 0.6:
                    z = env.zone_by_id(zid)
                    if z:
                        zdx = self.x - z.center[0]
                        zdy = self.y - z.center[1]
                        zd = math.hypot(zdx, zdy) or 1.0
                        if zd < 120:
                            avoid_x += (zdx / zd) * dens * 0.8
                            avoid_y += (zdy / zd) * dens * 0.8

        speed = config.BASE_SPEED * self.speed_mult
        if self.rerouted:
            speed *= 1.05

        desired_vx = (dx / dist) * speed + avoid_x
        desired_vy = (dy / dist) * speed + avoid_y

        # Smooth velocity
        smooth = 0.25 if self.panic else 0.18
        self.vx += (desired_vx - self.vx) * smooth
        self.vy += (desired_vy - self.vy) * smooth

        self.x += self.vx
        self.y += self.vy

        # Keep in walkable cells
        from abos.environment import world_to_cell

        cx, cy = world_to_cell(self.x, self.y)
        if not env.is_walkable(cx, cy):
            alt = env.nearest_walkable(cx, cy, radius=4)
            if alt:
                from abos.environment import cell_to_world
                self.x, self.y = cell_to_world(*alt)

        margin = config.AGENT_RADIUS + 2
        self.x = max(margin, min(config.SIM_WIDTH - margin, self.x))
        self.y = max(margin, min(config.SIM_HEIGHT - margin, self.y))

    def _current_waypoint(self) -> tuple[float, float] | None:
        if not self.path:
            return None
        idx = min(self.path_index, len(self.path) - 1)
        return self.path[idx]

    def at_destination(self) -> bool:
        if not self.path:
            return False
        wx, wy = self.path[-1]
        return math.hypot(wx - self.x, wy - self.y) < 14


def _pick_behavior() -> BehaviorType:
    r = random.random()
    cum = 0.0
    for name, weight in config.BEHAVIOR_WEIGHTS.items():
        cum += weight
        if r <= cum:
            return BehaviorType(name)
    return BehaviorType.COMPLIANT


def spawn_agents(count: int, env: FacilityEnvironment) -> list[Agent]:
    agents: list[Agent] = []
    journey = env.journey_order()
    entrance = env.zone_by_id("main_entrance")
    if not entrance:
        entrance = env.zones[0]

    for i in range(count):
        ex, ey = entrance.center
        x = ex + random.uniform(-entrance.width * 0.3, entrance.width * 0.3)
        y = ey + random.uniform(-entrance.height * 0.3, entrance.height * 0.3)
        agent = Agent(
            x=x, y=y,
            behavior=_pick_behavior(),
            journey=list(journey),
            journey_index=0,
            _uid=i,
        )
        agents.append(agent)
    return agents


def agents_near(agent: Agent, all_agents: list[Agent], radius: float = 35.0) -> list[Agent]:
    return [
        a for a in all_agents
        if a is not agent and (a.x - agent.x) ** 2 + (a.y - agent.y) ** 2 < radius ** 2
    ]
