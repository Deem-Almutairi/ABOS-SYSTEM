"""A* pathfinding with dynamic congestion-aware costs."""

from __future__ import annotations

import heapq
import math
from typing import Callable

from abos.environment import FacilityEnvironment, cell_to_world, world_to_cell


def heuristic(ax: int, ay: int, bx: int, by: int) -> float:
    return abs(ax - bx) + abs(ay - by)


def astar(
    env: FacilityEnvironment,
    start: tuple[int, int],
    goal: tuple[int, int],
    cost_fn: Callable[[int, int], float] | None = None,
) -> list[tuple[int, int]] | None:
    """Return list of (cx, cy) cells from start to goal, or None."""
    if cost_fn is None:
        cost_fn = lambda _x, _y: 1.0

    start = env.nearest_walkable(*start) or start
    goal = env.nearest_walkable(*goal) or goal

    if not env.is_walkable(*goal):
        return None

    open_set: list[tuple[float, int, int]] = []
    heapq.heappush(open_set, (0.0, start[0], start[1]))
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {start: 0.0}
    closed: set[tuple[int, int]] = set()

    neighbors = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)]

    while open_set:
        _, cx, cy = heapq.heappop(open_set)
        if (cx, cy) in closed:
            continue
        closed.add((cx, cy))

        if (cx, cy) == goal:
            path = [(cx, cy)]
            while (cx, cy) in came_from:
                cx, cy = came_from[(cx, cy)]
                path.append((cx, cy))
            path.reverse()
            return path

        for dx, dy in neighbors:
            nx, ny = cx + dx, cy + dy
            if not env.is_walkable(nx, ny) or (nx, ny) in closed:
                continue
            step = 1.414 if dx and dy else 1.0
            tentative = g_score[(cx, cy)] + step * cost_fn(nx, ny)
            if tentative < g_score.get((nx, ny), float("inf")):
                came_from[(nx, ny)] = (cx, cy)
                g_score[(nx, ny)] = tentative
                f = tentative + heuristic(nx, ny, goal[0], goal[1])
                heapq.heappush(open_set, (f, nx, ny))

    return None


def path_to_world(path: list[tuple[int, int]], step: int = 2) -> list[tuple[float, float]]:
    """Down-sample grid path to world waypoints."""
    if not path:
        return []
    waypoints = []
    for i in range(0, len(path), step):
        waypoints.append(cell_to_world(*path[i]))
    if path and waypoints[-1] != cell_to_world(*path[-1]):
        waypoints.append(cell_to_world(*path[-1]))
    return waypoints


def make_cost_fn(env: FacilityEnvironment, congestion: dict[str, float], predicted: set[str]) -> Callable[[int, int], float]:
    """Higher cost in congested / predicted zones."""

    def cost_fn(cx: int, cy: int) -> float:
        px, py = cell_to_world(cx, cy)
        zone = env.zone_at(px, py)
        if zone is None:
            return 1.0
        base = 1.0
        if zone.is_bottleneck:
            base += 0.5
        d = congestion.get(zone.id, 0.0)
        base += d * 6.0
        if zone.id in predicted:
            base += 4.0
        return base

    return cost_fn


def plan_route(
    env: FacilityEnvironment,
    from_pos: tuple[float, float],
    to_zone_id: str,
    congestion: dict[str, float],
    predicted: set[str],
) -> list[tuple[float, float]]:
    zone = env.zone_by_id(to_zone_id)
    if zone is None:
        return []
    sc = world_to_cell(*from_pos)
    gc = world_to_cell(*zone.center)
    gc = env.nearest_walkable(*gc) or gc
    cost_fn = make_cost_fn(env, congestion, predicted)
    path = astar(env, sc, gc, cost_fn)
    if path is None:
        return [zone.center]
    return path_to_world(path)
