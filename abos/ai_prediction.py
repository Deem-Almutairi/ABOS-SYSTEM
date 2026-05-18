"""AI congestion prediction: density growth, flow, influx, time-to-event."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from abos import config
from abos.environment import FacilityEnvironment, OperationalZone


@dataclass
class ZoneForecast:
    zone: OperationalZone
    risk_score: float
    confidence: float
    congested: bool
    predicted: bool
    minutes_until: float | None
    trend: float
    flow_factor: float
    alert_message: str = ""

    @property
    def risk_level(self) -> str:
        if self.risk_score >= 0.85:
            return "CRITICAL"
        if self.risk_score >= 0.65:
            return "HIGH"
        if self.risk_score >= 0.45:
            return "MEDIUM"
        return "LOW"


@dataclass
class CongestionPredictor:
    density_history: dict[str, deque[float]] = field(default_factory=dict)
    window: int = config.PREDICT_WINDOW
    alerts: list[str] = field(default_factory=list)

    def _hist(self, zone_id: str) -> deque[float]:
        if zone_id not in self.density_history:
            self.density_history[zone_id] = deque(maxlen=self.window)
        return self.density_history[zone_id]

    def update(self, env: FacilityEnvironment) -> list[ZoneForecast]:
        forecasts: list[ZoneForecast] = []
        self.alerts = []

        for zone in env.zones:
            hist = self._hist(zone.id)
            hist.append(zone.density)

            trend = 0.0
            if len(hist) >= 2:
                trend = hist[-1] - hist[-2]
            if len(hist) >= 12:
                recent = sum(list(hist)[-6:]) / 6
                older = sum(list(hist)[:6]) / 6
                trend = recent - older

            # Flow factor: slow movement + rising density = worse
            norm_flow = min(1.0, zone.flow_speed / config.BASE_SPEED) if zone.flow_speed else 0.3
            flow_factor = 1.0 - norm_flow

            influx_norm = min(1.0, zone.influx / max(1, zone.agent_count))

            risk = (
                config.W_DENSITY * zone.density
                + config.W_GROWTH * max(0.0, trend) * 8
                + config.W_FLOW * flow_factor * zone.density
                + config.W_INFLUX * influx_norm
            )
            if zone.is_bottleneck:
                risk *= 1.15
            risk = min(1.0, max(0.0, risk))

            confidence = min(1.0, len(hist) / 20) * (0.5 + 0.5 * abs(trend) * 10)
            confidence = min(1.0, confidence)

            congested = zone.density >= config.CONGESTION_THRESHOLD
            predicted = (
                risk >= config.CONGESTION_THRESHOLD * 0.85
                or (zone.density >= config.DENSITY_MEDIUM and trend > 0.015)
                or (zone.is_bottleneck and trend > 0.01 and zone.density > 0.4)
            )

            minutes_until = None
            if trend > 0.001 and zone.density < config.CONGESTION_THRESHOLD:
                frames_left = (config.CONGESTION_THRESHOLD - zone.density) / trend
                minutes_until = max(0.5, frames_left / config.FRAMES_PER_MINUTE)
            elif congested:
                minutes_until = 0.0

            alert_message = ""
            if predicted and not congested and minutes_until is not None:
                alert_message = (
                    f"Predicted congestion in {zone.label} within {minutes_until:.0f} min"
                )
                self.alerts.append(alert_message)
            elif congested:
                alert_message = f"ACTIVE congestion in {zone.label}"
                self.alerts.append(alert_message)

            forecasts.append(
                ZoneForecast(
                    zone=zone,
                    risk_score=risk,
                    confidence=confidence,
                    congested=congested,
                    predicted=predicted,
                    minutes_until=minutes_until,
                    trend=trend,
                    flow_factor=flow_factor,
                    alert_message=alert_message,
                )
            )

        return forecasts
