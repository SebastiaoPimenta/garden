from __future__ import annotations

import math
from typing import Iterable

from .garden import Plot


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


def greedy_visit_order(
    plots: list[Plot],
    start: tuple[int, int] | None = None,
) -> list[Plot]:
    """Ordem de visita: vizinho mais próximo (estilo cobrinha / bomberman)."""
    if not plots:
        return []

    remaining = list(plots)
    if start is None:
        # Começa perto do centro-inferior do grid
        avg_row = sum(p.row for p in plots) // len(plots)
        avg_col = sum(p.col for p in plots) // len(plots)
        pos = (avg_row, avg_col)
    else:
        pos = start

    order: list[Plot] = []
    while remaining:
        nearest = min(remaining, key=lambda p: manhattan(pos, (p.row, p.col)))
        order.append(nearest)
        remaining.remove(nearest)
        pos = (nearest.row, nearest.col)
    return order


def path_between(a: tuple[int, int], b: tuple[int, int]) -> list[tuple[int, int]]:
    """Caminho em grade (passos ortogonais), priorizando eixo dominante."""
    path: list[tuple[int, int]] = [a]
    row, col = a
    tr, tc = b
    while (row, col) != (tr, tc):
        dr = tr - row
        dc = tc - col
        if abs(dr) >= abs(dc) and dr != 0:
            row += math.copysign(1, dr)
        elif dc != 0:
            col += math.copysign(1, dc)
        else:
            row += math.copysign(1, dr)
        path.append((row, col))
    return path


def expand_route(ordered_plots: Iterable[Plot], start: tuple[int, int]) -> list[tuple[str, tuple[int, int], str]]:
    """
    Expande rota em passos: (tipo, posição, view).
    tipo: 'walk' | 'water'
    """
    steps: list[tuple[str, tuple[int, int], str]] = []
    pos = start
    last_view = "front"
    for plot in ordered_plots:
        target = (plot.row, plot.col)
        segment = path_between(pos, target)
        for i in range(1, len(segment)):
            prev = segment[i - 1]
            cur = segment[i]
            dr = cur[0] - prev[0]
            dc = cur[1] - prev[1]
            last_view = direction_view(dr, dc)
            steps.append(("walk", cur, last_view))
        steps.append(("water", target, last_view))
        pos = target
    return steps
