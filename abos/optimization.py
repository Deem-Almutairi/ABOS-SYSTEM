"""Adaptive routing and congestion-aware path optimization."""

from __future__ import annotations

from dataclasses import dataclass, field

from abos import config
from abos.agents import Agent
from abos.ai_prediction import ZoneForecast
from abos.environment import FacilityEnvironment
from abos.pathfinding import plan_route


@dataclass
class ActiveAlert:
    zone_id: str
    message: str
    risk_level: str
    confidence: float
    frames_left: int = 180


@dataclass
class AdaptiveOptimizer:
    alerts: list[ActiveAlert] = field(default_factory=list)
    reroute_count: int = 0
    paths_computed: int = 0
    _replan_timer: dict[int, int] = field(default_factory=dict)

    def process(
        self,
        env: FacilityEnvironment,
        agents: list[Agent],
        forecasts: list[ZoneForecast],
    ) -> list[str]:
        congestion = {z.id: z.density for z in env.zones}
        predicted_ids = {f.zone.id for f in forecasts if f.predicted}
        hot_ids = {f.zone.id for f in forecasts if f.congested or f.predicted}

        messages: list[str] = []
        for f in forecasts:
            if f.alert_message:
                messages.append(f.alert_message)
                self._upsert_alert(f)

        replans_left = config.MAX_REPLANS_PER_FRAME

        for agent in agents:
            uid = agent._uid
            timer = self._replan_timer.get(uid, 0)
            if timer > 0:
                self._replan_timer[uid] = timer - 1

            current_zone = env.zone_at(agent.x, agent.y)
            target_id = agent.target_zone_id

            # Journey progression (only when route actually completed)
            if (
                agent.path
                and agent.at_destination()
                and agent.wait_timer <= 0
                and target_id
            ):
                next_zone = agent.advance_journey()
                if next_zone:
                    target_id = next_zone
                else:
                    agent.journey_index = 0
                    target_id = agent.target_zone_id

            needs_replan = False
            if not agent.path:
                needs_replan = True
            elif target_id and target_id in hot_ids:
                needs_replan = True
            elif (
                current_zone
                and current_zone.id in hot_ids
                and current_zone.density > 0.7
            ):
                needs_replan = True

            if needs_replan and self._replan_timer.get(uid, 0) <= 0 and replans_left > 0:
                self._assign_route(
                    agent, env, congestion, predicted_ids,
                    reroute=bool(target_id and target_id in hot_ids),
                )
                self._replan_timer[uid] = config.PATH_REPLAN_INTERVAL
                replans_left -= 1

        self._tick_alerts()
        return messages + [a.message for a in self.alerts]

    def bootstrap_routes(
        self,
        env: FacilityEnvironment,
        agents: list[Agent],
        max_count: int | None = None,
    ) -> int:
        """Assign initial paths in small batches (call before/at startup)."""
        limit = max_count or config.MAX_REPLANS_PER_FRAME
        congestion = {z.id: 0.0 for z in env.zones}
        assigned = 0
        for agent in agents:
            if agent.path:
                continue
            target_id = agent.target_zone_id
            if not target_id:
                continue
            self._assign_route(agent, env, congestion, set(), reroute=False)
            self._replan_timer[agent._uid] = 5
            assigned += 1
            if assigned >= limit:
                break
        return assigned

    def _assign_route(
        self,
        agent: Agent,
        env: FacilityEnvironment,
        congestion: dict[str, float],
        predicted: set[str],
        reroute: bool,
    ) -> None:
        target_id = agent.target_zone_id
        if not target_id:
            return

        if reroute and agent.behavior.value == "impatient":
            gates = env.gate_zones()
            if gates and "gate" in target_id:
                target_id = min(gates, key=lambda g: g.density).id

        waypoints = plan_route(env, (agent.x, agent.y), target_id, congestion, predicted)
        if waypoints:
            agent.set_path(waypoints, rerouted=reroute)
            if reroute:
                self.reroute_count += 1
            self.paths_computed += 1

    def _upsert_alert(self, forecast: ZoneForecast) -> None:
        zid = forecast.zone.id
        for a in self.alerts:
            if a.zone_id == zid:
                a.message = forecast.alert_message
                a.risk_level = forecast.risk_level
                a.confidence = forecast.confidence
                a.frames_left = 180
                return
        self.alerts.append(
            ActiveAlert(
                zone_id=zid,
                message=forecast.alert_message,
                risk_level=forecast.risk_level,
                confidence=forecast.confidence,
            )
        )

    def _tick_alerts(self) -> None:
        for a in self.alerts:
            a.frames_left -= 1
        self.alerts = [a for a in self.alerts if a.frames_left > 0]

    def force_evacuation_routes(self, env: FacilityEnvironment, agents: list[Agent]) -> None:
        exit_zone = env.zone_by_id("exit") or env.zone_by_id("main_entrance")
        if not exit_zone:
            return
        for agent in agents:
            agent.panic = True
            agent.journey = [exit_zone.id]
            agent.journey_index = 0
            waypoints = plan_route(env, (agent.x, agent.y), exit_zone.id, {}, set())
            if waypoints:
                agent.set_path(waypoints, rerouted=True)
                self.reroute_count += 1
