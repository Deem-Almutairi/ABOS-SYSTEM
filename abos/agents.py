"""2D crowd agents with simple steering and rerouting."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from abos import config


@dataclass
class Agent:
    x: float
    y: float
    target_x: float
    target_y: float
    rerouted: bool = False
    _vx: float = field(default=0.0, repr=False)
    _vy: float = field(default=0.0, repr=False)

    def update(self, width: int, height: int) -> None:
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.hypot(dx, dy)

        if dist < 12:
            self._pick_new_target(width, height)
            dx = self.target_x - self.x
            dy = self.target_y - self.y
            dist = math.hypot(dx, dy) or 1.0

        speed = config.AGENT_SPEED * (0.7 if self.rerouted else 1.0)
        self._vx = (dx / dist) * speed
        self._vy = (dy / dist) * speed
        self.x += self._vx
        self.y += self._vy

        margin = config.AGENT_RADIUS + 2
        self.x = max(margin, min(width - margin, self.x))
        self.y = max(margin, min(height - margin, self.y))

    def _pick_new_target(self, width: int, height: int) -> None:
        pad = 40
        self.target_x = random.uniform(pad, width - pad)
        self.target_y = random.uniform(pad, height - pad)

    def set_target(self, x: float, y: float) -> None:
        self.target_x = x
        self.target_y = y
        self.rerouted = True

    def clear_reroute(self) -> None:
        self.rerouted = False


def spawn_agents(count: int, width: int, height: int) -> list[Agent]:
    agents: list[Agent] = []
    for _ in range(count):
        x = random.uniform(40, width - 40)
        y = random.uniform(40, height - 40)
        agent = Agent(x=x, y=y, target_x=x, target_y=y)
        agent._pick_new_target(width, height)
        agents.append(agent)
    return agents
