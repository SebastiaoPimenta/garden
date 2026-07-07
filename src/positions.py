from __future__ import annotations

from .config import (
    CELL_GAP,
    CELL_SIZE,
    CHARACTER_HEIGHT,
    CHARACTER_WIDTH,
    COLS,
    FLOWER_HEIGHT,
    FLOWER_WIDTH,
    GRID_OVERFLOW_TOP,
    PADDING,
    ROWS,
)

GRID_OFFSET_Y = PADDING + GRID_OVERFLOW_TOP


def cell_xy(row: int, col: int) -> tuple[float, float]:
    x = PADDING + col * (CELL_SIZE + CELL_GAP)
    y = GRID_OFFSET_Y + row * (CELL_SIZE + CELL_GAP)
    return x, y


def cell_feet_xy(row: int, col: int) -> tuple[float, float]:
    x, y = cell_xy(row, col)
    return x + CELL_SIZE / 2, y + CELL_SIZE


def character_topleft(feet_x: float, feet_y: float) -> tuple[float, float]:
    return feet_x - CHARACTER_WIDTH / 2, feet_y - CHARACTER_HEIGHT


def character_topleft_at_cell(row: int, col: int) -> tuple[float, float]:
    return character_topleft(*cell_feet_xy(row, col))


def flower_topleft(feet_x: float, feet_y: float) -> tuple[float, float]:
    return feet_x - FLOWER_WIDTH / 2, feet_y - FLOWER_HEIGHT


def flower_topleft_at_cell(row: int, col: int) -> tuple[float, float]:
    return flower_topleft(*cell_feet_xy(row, col))


def svg_size() -> tuple[int, int]:
    w = PADDING * 2 + COLS * CELL_SIZE + (COLS - 1) * CELL_GAP
    grid_h = ROWS * CELL_SIZE + (ROWS - 1) * CELL_GAP
    h = PADDING + GRID_OVERFLOW_TOP + grid_h + PADDING
    return w, h


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t
