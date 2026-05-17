"""Rule-based congestion prediction from density history and trends."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from abos import config
from abos.zones import Zone, ZoneGrid


@dataclass
class ZoneForecast:
    zone: Zone
    risk_score: float  # 0–1
    congested: bool
    predicted_congestion: bool
    trend: float  # positive = density rising


@dataclass
class CongestionPredictor:
    history: dict[int, deque[float]] = field(default_factory=dict)
    window: int = config.PREDICT_WINDOW

    def _history_for(self, zone: Zone) -> deque[float]:
        key = id(zone)
        if key not in self.history:
            self.history[key] = deque(maxlen=self.window)
        return self.history[key]

    def update(self, grid: ZoneGrid) -> list[ZoneForecast]:
        forecasts: list[ZoneForecast] = []

        for zone in grid.zones:
            hist = self._history_for(zone)
            hist.append(zone.density)

            trend = 0.0
            if len(hist) >= 2:
                trend = hist[-1] - hist[-2]
            if len(hist) >= 10:
                trend = (sum(list(hist)[-5:]) / 5) - (sum(list(hist)[:5]) / 5)

            risk = zone.density + config.TREND_WEIGHT * max(0.0, trend) * 5
            risk = min(1.0, max(0.0, risk))

            congested = zone.density >= config.CONGESTION_THRESHOLD
            predicted = risk >= config.CONGESTION_THRESHOLD or (
                zone.density >= config.DENSITY_MEDIUM and trend > 0.02
            )

            forecasts.append(
                ZoneForecast(
                    zone=zone,
                    risk_score=risk,
                    congested=congested,
                    predicted_congestion=predicted,
                    trend=trend,
                )
            )

        return forecasts
