"""Zone grid for crowd density detection."""

from __future__ import annotations

from dataclasses import dataclass, field

from abos import config


@dataclass
class Zone:
    col: int
    row: int
    x: float
    y: float
    width: float
    height: float
    agent_count: int = 0
    density: float = 0.0  # 0–1 relative to capacity

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px < self.x + self.width and self.y <= py < self.y + self.height


@dataclass
class ZoneGrid:
    zones: list[Zone] = field(default_factory=list)
    cols: int = config.ZONE_COLS
    rows: int = config.ZONE_ROWS
    capacity_per_zone: float = 1.0

    @classmethod
    def from_screen(cls, screen_w: int, screen_h: int) -> ZoneGrid:
        pad = config.ZONE_PADDING
        usable_w = screen_w - 2 * pad
        usable_h = screen_h - 2 * pad
        zone_w = usable_w / config.ZONE_COLS
        zone_h = usable_h / config.ZONE_ROWS
        zones: list[Zone] = []

        for row in range(config.ZONE_ROWS):
            for col in range(config.ZONE_COLS):
                zones.append(
                    Zone(
                        col=col,
                        row=row,
                        x=pad + col * zone_w,
                        y=pad + row * zone_h,
                        width=zone_w,
                        height=zone_h,
                    )
                )

        grid = cls(zones=zones)
        grid.capacity_per_zone = max(4.0, config.NUM_AGENTS / (config.ZONE_COLS * config.ZONE_ROWS) * 1.2)
        return grid

    def zone_at(self, px: float, py: float) -> Zone | None:
        for zone in self.zones:
            if zone.contains(px, py):
                return zone
        return None

    def update_counts(self, positions: list[tuple[float, float]]) -> None:
        for zone in self.zones:
            zone.agent_count = 0

        for px, py in positions:
            zone = self.zone_at(px, py)
            if zone:
                zone.agent_count += 1

        for zone in self.zones:
            zone.density = min(1.0, zone.agent_count / self.capacity_per_zone)

    def densities(self) -> list[float]:
        return [z.density for z in self.zones]

    def sparsest_zone(self, exclude: Zone | None = None) -> Zone:
        candidates = [z for z in self.zones if z is not exclude]
        return min(candidates, key=lambda z: z.density)
