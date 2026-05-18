"""Realistic facility layout: walls, hallways, operational zones."""

from __future__ import annotations

from dataclasses import dataclass, field

from abos import config


@dataclass
class OperationalZone:
    id: str
    label: str
    x: float
    y: float
    width: float
    height: float
    capacity: float
    is_bottleneck: bool = False
    is_exit: bool = False
    agent_count: int = 0
    density: float = 0.0
    flow_speed: float = 0.0
    influx: float = 0.0

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def display_name(self) -> str:
        return self.label

    def contains(self, px: float, py: float) -> bool:
        return self.x <= px < self.x + self.width and self.y <= py < self.y + self.height

    def contains_cell(self, cx: int, cy: int) -> bool:
        px, py = cell_to_world(cx, cy)
        return self.contains(px, py)


def cell_to_world(cx: int, cy: int) -> tuple[float, float]:
    cs = config.CELL_SIZE
    return (cx * cs + cs / 2, cy * cs + cs / 2)


def world_to_cell(px: float, py: float) -> tuple[int, int]:
    cs = config.CELL_SIZE
    return (int(px // cs), int(py // cs))


@dataclass
class FacilityEnvironment:
    """Grid-based walkable map with labeled operational zones."""

    grid: list[list[bool]] = field(default_factory=list)  # True = walkable
    zones: list[OperationalZone] = field(default_factory=list)
    cols: int = 0
    rows: int = 0

    @classmethod
    def build_airport(cls) -> FacilityEnvironment:
        cols, rows = config.GRID_COLS, config.GRID_ROWS
        grid = [[False] * cols for _ in range(rows)]

        # Outer boundary walls (walkable interior carved by rooms)
        for cx in range(cols):
            for cy in range(rows):
                grid[cy][cx] = True

        def wall_rect(x0: int, y0: int, x1: int, y1: int) -> None:
            for cy in range(y0, y1):
                for cx in range(x0, x1):
                    if 0 <= cx < cols and 0 <= cy < rows:
                        grid[cy][cx] = False

        # ── Structural walls (airport terminal layout) ───────────────────────
        # Top block — waiting lounge
        wall_rect(0, 0, cols, 8)
        wall_rect(0, 8, 12, 22)
        wall_rect(52, 8, cols, 22)

        # Security corridor walls (bottleneck)
        wall_rect(0, 22, 18, 28)
        wall_rect(38, 22, cols, 28)

        # Check-in wing (left)
        wall_rect(0, 28, 14, 42)
        wall_rect(0, 42, cols, rows)  # bottom strip reserved for entrance

        # Gate wing dividers (right)
        wall_rect(58, 8, 62, 22)
        wall_rect(58, 14, cols, 18)

        # Center column between gates
        wall_rect(48, 8, 52, 48)

        # Bottom entrance channel
        wall_rect(0, 48, 28, rows)
        wall_rect(48, 48, cols, rows)

        # Re-open hallways
        for cx in range(18, 38):
            for cy in range(22, 28):
                grid[cy][cx] = True
        for cx in range(14, 48):
            for cy in range(28, 48):
                grid[cy][cx] = True
        for cx in range(28, 48):
            for cy in range(42, rows):
                grid[cy][cx] = True
        for cy in range(8, 22):
            for cx in range(12, 52):
                grid[cy][cx] = True
        for cy in range(8, 48):
            for cx in range(52, cols):
                grid[cy][cx] = True

        cs = config.CELL_SIZE
        zones = [
            OperationalZone(
                "main_entrance", "Main Entrance",
                28 * cs, 48 * cs, 20 * cs, 12 * cs, capacity=28,
            ),
            OperationalZone(
                "check_in", "Check-in Area",
                14 * cs, 28 * cs, 20 * cs, 14 * cs, capacity=22,
            ),
            OperationalZone(
                "security", "Security Check",
                18 * cs, 22 * cs, 20 * cs, 6 * cs, capacity=14, is_bottleneck=True,
            ),
            OperationalZone(
                "waiting_lounge", "Waiting Lounge",
                12 * cs, 8 * cs, 36 * cs, 14 * cs, capacity=35,
            ),
            OperationalZone(
                "gate_a", "Gate A",
                52 * cs, 8 * cs, 8 * cs, 6 * cs, capacity=12,
            ),
            OperationalZone(
                "gate_b", "Gate B",
                52 * cs, 18 * cs, 8 * cs, 6 * cs, capacity=12,
            ),
            OperationalZone(
                "gate_c", "Gate C",
                62 * cs, 8 * cs, 18 * cs, 16 * cs, capacity=16,
            ),
            OperationalZone(
                "bottleneck", "Corridor Bottleneck",
                18 * cs, 24 * cs, 20 * cs, 4 * cs, capacity=8, is_bottleneck=True,
            ),
            OperationalZone(
                "exit", "Emergency Exit",
                2 * cs, 2 * cs, 8 * cs, 5 * cs, capacity=20, is_exit=True,
            ),
        ]

        env = cls(grid=grid, zones=zones, cols=cols, rows=rows)
        return env

    @classmethod
    def build(cls) -> FacilityEnvironment:
        mode = config.FACILITY_MODE
        if mode == "hospital":
            return cls.build_hospital()
        if mode == "transit":
            return cls.build_transit()
        return cls.build_airport()

    @classmethod
    def build_hospital(cls) -> FacilityEnvironment:
        env = cls.build_airport()
        labels = {
            "main_entrance": "Emergency Entrance",
            "check_in": "Registration",
            "security": "Triage",
            "waiting_lounge": "Patient Waiting",
            "gate_a": "Ward A",
            "gate_b": "Ward B",
            "gate_c": "ICU",
            "bottleneck": "Critical Corridor",
            "exit": "Ambulance Bay",
        }
        for z in env.zones:
            z.label = labels.get(z.id, z.label)
        return env

    @classmethod
    def build_transit(cls) -> FacilityEnvironment:
        env = cls.build_airport()
        labels = {
            "main_entrance": "Station Entrance",
            "check_in": "Ticket Hall",
            "security": "Fare Gates",
            "waiting_lounge": "Platform Concourse",
            "gate_a": "Platform 1",
            "gate_b": "Platform 2",
            "gate_c": "Platform 3",
            "bottleneck": "Stairwell",
            "exit": "Street Exit",
        }
        for z in env.zones:
            z.label = labels.get(z.id, z.label)
        return env

    def is_walkable(self, cx: int, cy: int) -> bool:
        if not (0 <= cx < self.cols and 0 <= cy < self.rows):
            return False
        return self.grid[cy][cx]

    def nearest_walkable(self, cx: int, cy: int, radius: int = 6) -> tuple[int, int] | None:
        if self.is_walkable(cx, cy):
            return (cx, cy)
        for r in range(1, radius + 1):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    nx, ny = cx + dx, cy + dy
                    if self.is_walkable(nx, ny):
                        return (nx, ny)
        return None

    def zone_at(self, px: float, py: float) -> OperationalZone | None:
        for zone in self.zones:
            if zone.contains(px, py):
                return zone
        return None

    def zone_by_id(self, zone_id: str) -> OperationalZone | None:
        for z in self.zones:
            if z.id == zone_id:
                return z
        return None

    def journey_order(self) -> list[str]:
        if config.FACILITY_MODE == "hospital":
            return ["main_entrance", "check_in", "security", "waiting_lounge", "gate_a"]
        if config.FACILITY_MODE == "transit":
            return ["main_entrance", "check_in", "security", "waiting_lounge", "gate_b"]
        return ["main_entrance", "check_in", "security", "waiting_lounge", "gate_a"]

    def gate_zones(self) -> list[OperationalZone]:
        return [z for z in self.zones if z.id.startswith("gate_")]

    def update_metrics(self, agents: list) -> None:
        for z in self.zones:
            z.agent_count = 0
            z.flow_speed = 0.0
            z.influx = 0.0

        for agent in agents:
            zone = self.zone_at(agent.x, agent.y)
            if zone:
                zone.agent_count += 1
                speed = (agent.vx ** 2 + agent.vy ** 2) ** 0.5
                zone.flow_speed += speed
                # influx: agent moving toward zone center
                zx, zy = zone.center
                dx, dy = zx - agent.x, zy - agent.y
                dot = agent.vx * dx + agent.vy * dy
                if dot > 0:
                    zone.influx += 1

        for z in self.zones:
            if z.agent_count > 0:
                z.flow_speed /= z.agent_count
            z.density = min(1.0, z.agent_count / z.capacity)

    def cell_density_map(self, agents: list, heat_cols: int = 40, heat_rows: int = 30) -> list[list[float]]:
        """Fine heatmap grid for visualization."""
        heat = [[0.0] * heat_cols for _ in range(heat_rows)]
        cell_w = config.SIM_WIDTH / heat_cols
        cell_h = config.SIM_HEIGHT / heat_rows
        for agent in agents:
            hc = min(heat_cols - 1, int(agent.x / cell_w))
            hr = min(heat_rows - 1, int(agent.y / cell_h))
            heat[hr][hc] += 1.0
        cap = max(1.0, config.NUM_AGENTS / (heat_cols * heat_rows) * 4)
        return [[min(1.0, v / cap) for v in row] for row in heat]
