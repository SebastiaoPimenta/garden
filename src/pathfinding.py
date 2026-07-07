from __future__ import annotations

from collections import deque
from typing import Iterable

from .garden import Garden, Plot


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def direction_view(dr: int, dc: int) -> str:
    """View do personagem conforme direção do movimento (row, col)."""
    if dr < 0:
        return "back"
    if dr > 0:
        return "front"
    if dc < 0:
        return "left"
    if dc > 0:
        return "right"
    return "front"


def facing_toward(stand: tuple[int, int], target: tuple[int, int]) -> str:
    """View do personagem parado em `stand` olhando para `target`."""
    sr, sc = stand
    tr, tc = target
    return direction_view(tr - sr, tc - sc)


def _in_bounds(garden: Garden, row: int, col: int) -> bool:
    return 0 <= row < garden.rows and 0 <= col < garden.cols


def _is_plot(garden: Garden, row: int, col: int) -> bool:
    return garden.grid[row][col] > 0


def watering_spots(garden: Garden, plot: Plot) -> list[tuple[int, int]]:
    """Células adjacentes ao plot onde o personagem pode ficar para regar."""
    spots: list[tuple[int, int]] = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        r, c = plot.row + dr, plot.col + dc
        if _in_bounds(garden, r, c):
            spots.append((r, c))
    return spots


def choose_watering_spot(
    garden: Garden,
    plot: Plot,
    from_pos: tuple[int, int],
) -> tuple[int, int] | None:
    """
    Escolhe célula adjacente para regar, preferindo grama (não-plot).
    Se só houver plots adjacentes, usa o necessário.
    """
    spots = watering_spots(garden, plot)
    if not spots:
        return None
    empty = [s for s in spots if not _is_plot(garden, *s)]
    pool = empty if empty else spots
    return min(pool, key=lambda s: manhattan(from_pos, s))


def _walkable(
    garden: Garden,
    row: int,
    col: int,
    avoid_plots: bool,
    allowed: set[tuple[int, int]],
) -> bool:
    if not _in_bounds(garden, row, col):
        return False
    if (row, col) in allowed:
        return True
    if avoid_plots and _is_plot(garden, row, col):
        return False
    return True


def path_avoiding_plots(
    garden: Garden,
    start: tuple[int, int],
    goal: tuple[int, int],
    *,
    avoid_plots: bool = True,
) -> list[tuple[int, int]]:
    """
    Caminho em grade (BFS). Evita plots quando `avoid_plots=True`.
    Se não houver rota sem passar em plots, tenta novamente permitindo.
    """
    allowed = {start, goal}

    def bfs(avoid: bool) -> list[tuple[int, int]] | None:
        if start == goal:
            return [start]
        queue: deque[tuple[int, int]] = deque([start])
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        while queue:
            cur = queue.popleft()
            if cur == goal:
                path: list[tuple[int, int]] = []
                while cur is not None:
                    path.append(cur)
                    cur = came_from[cur]
                path.reverse()
                return path
            r, c = cur
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                nxt = (nr, nc)
                if nxt in came_from:
                    continue
                if not _walkable(garden, nr, nc, avoid, allowed):
                    continue
                came_from[nxt] = cur
                queue.append(nxt)
        return None

    path = bfs(avoid_plots)
    if path is None and avoid_plots:
        path = bfs(False)
    return path if path is not None else [start, goal]


def greedy_visit_order(
    garden: Garden,
    plots: list[Plot],
    start: tuple[int, int] | None = None,
) -> list[Plot]:
    """Ordem de visita pelo vizinho mais próximo (posição de approach)."""
    if not plots:
        return []

    remaining = list(plots)
    pos = start if start is not None else (0, 0)

    order: list[Plot] = []
    while remaining:
        def approach_distance(p: Plot) -> int:
            spot = choose_watering_spot(garden, p, pos)
            if spot is None:
                return manhattan(pos, (p.row, p.col))
            return manhattan(pos, spot)

        nearest = min(remaining, key=approach_distance)
        order.append(nearest)
        remaining.remove(nearest)
        spot = choose_watering_spot(garden, nearest, pos)
        pos = spot if spot is not None else (nearest.row, nearest.col)
    return order


RouteStep = tuple[str, tuple[int, int], str, Plot | None]


def expand_route(
    garden: Garden,
    ordered_plots: Iterable[Plot],
    start: tuple[int, int],
) -> list[RouteStep]:
    """
    Expande rota: walk → idle (olhando pro plot) → water.
    Cada passo: (tipo, posição, view, plot_ou_None).
    """
    steps: list[RouteStep] = []
    pos = start

    for plot in ordered_plots:
        stand = choose_watering_spot(garden, plot, pos)
        if stand is None:
            continue

        segment = path_avoiding_plots(garden, pos, stand)
        for i in range(1, len(segment)):
            prev = segment[i - 1]
            cur = segment[i]
            dr = cur[0] - prev[0]
            dc = cur[1] - prev[1]
            view = direction_view(dr, dc)
            steps.append(("walk", cur, view, None))

        face = facing_toward(stand, (plot.row, plot.col))
        steps.append(("idle", stand, face, plot))
        steps.append(("water", stand, face, plot))
        pos = stand

    return steps
