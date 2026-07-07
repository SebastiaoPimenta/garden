from __future__ import annotations

import random
from dataclasses import dataclass, field

from .config import CHARACTER_HEIGHT, END_POSITION, START_POSITION, TIMING
from .garden import Garden, Plot, SpriteCatalog
from .pathfinding import (
    direction_view,
    expand_route,
    greedy_visit_order,
    path_avoiding_plots,
)
from .positions import character_topleft, cell_feet_xy, lerp


@dataclass
class WalkKeyframe:
    time: float
    x: float
    y: float
    view: str
    frame_index: int


@dataclass
class IdleKeyframe:
    time: float
    x: float
    y: float
    view: str
    frame_index: int


@dataclass
class WaterKeyframe:
    time: float
    x: float
    y: float
    view: str
    frame_index: int
    plot: Plot


@dataclass
class GrowthKeyframe:
    time: float
    row: int
    col: int
    tier: int
    stage: int  # 1–4


@dataclass
class WaitingKeyframe:
    time: float
    x: float
    y: float
    frame_index: int


@dataclass
class EmojiKeyframe:
    time: float
    x: float
    y: float
    emoji: str
    offset_y: float = 0.0


@dataclass
class AnimationTimeline:
    walk: list[WalkKeyframe] = field(default_factory=list)
    idle: list[IdleKeyframe] = field(default_factory=list)
    water: list[WaterKeyframe] = field(default_factory=list)
    growth: list[GrowthKeyframe] = field(default_factory=list)
    waiting: list[WaitingKeyframe] = field(default_factory=list)
    emojis: list[EmojiKeyframe] = field(default_factory=list)
    total_duration: float = 0.0

    @property
    def watered_plots(self) -> list[tuple[int, int]]:
        return sorted({(w.plot.row, w.plot.col) for w in self.water})


WAITING_EMOJIS = ["❤️", "💻", "👩‍💻", "✨", "🌸", "💖", "🧑‍💻", "💚"]


def _walk_substeps(view: str, sprites: SpriteCatalog | None, timing) -> int:
    if sprites:
        frames = sprites.character_frames(view, "walk")
        if len(frames) >= 2:
            return len(frames)
    return timing.walk_substeps


def _append_walk_segment(
    tl: AnimationTimeline,
    from_rc: tuple[int, int],
    to_rc: tuple[int, int],
    view: str,
    t_start: float,
    timing,
    sprites: SpriteCatalog | None,
) -> float:
    """Interpola posição entre duas células e alterna frames de caminhada."""
    substeps = _walk_substeps(view, sprites, timing)
    feet_from = cell_feet_xy(*from_rc)
    feet_to = cell_feet_xy(*to_rc)
    dt = timing.walk_step_duration / substeps

    for i in range(substeps):
        progress = (i + 1) / substeps
        fx = lerp(feet_from[0], feet_to[0], progress)
        fy = lerp(feet_from[1], feet_to[1], progress)
        x, y = character_topleft(fx, fy)
        tl.walk.append(
            WalkKeyframe(
                time=t_start + i * dt,
                x=x,
                y=y,
                view=view,
                frame_index=i,
            )
        )

    return t_start + timing.walk_step_duration


def _random_growth_delay(timing) -> float:
    lo = min(timing.growth_stage_min, timing.growth_stage_max)
    hi = max(timing.growth_stage_min, timing.growth_stage_max)
    if lo == hi:
        return lo
    return random.uniform(lo, hi)


def build_timeline(
    garden: Garden,
    start_pos: tuple[int, int] | None = None,
    timing=TIMING,
    sprites: SpriteCatalog | None = None,
    growth_seed: int | None = None,
) -> AnimationTimeline:
    plots = garden.plots_to_water()
    start_pos = START_POSITION if start_pos is None else start_pos
    end_pos = END_POSITION
    if growth_seed is not None:
        random.seed(growth_seed)
    order = greedy_visit_order(garden, plots, start_pos)

    route = expand_route(garden, order, start_pos)
    tl = AnimationTimeline()
    t = 0.0
    prev_pos = start_pos
    watered_at: dict[tuple[int, int], float] = {}

    for kind, pos, view, plot in route:
        row, col = pos
        if kind == "walk":
            t = _append_walk_segment(tl, prev_pos, pos, view, t, timing, sprites)
            prev_pos = pos
        elif kind == "idle":
            if plot is None:
                continue
            cx, cy = character_topleft(*cell_feet_xy(row, col))
            for fi in range(2):
                tl.idle.append(
                    IdleKeyframe(
                        time=t,
                        x=cx,
                        y=cy,
                        view=view,
                        frame_index=fi,
                    )
                )
                t += timing.idle_before_water
            prev_pos = pos
        elif kind == "water":
            if plot is None:
                continue
            cx, cy = character_topleft(*cell_feet_xy(row, col))
            for fi in range(3):
                tl.water.append(
                    WaterKeyframe(
                        time=t,
                        x=cx,
                        y=cy,
                        view=view,
                        frame_index=fi,
                        plot=plot,
                    )
                )
                t += timing.water_frame
            watered_at[(plot.row, plot.col)] = t
            prev_pos = pos

    if prev_pos != end_pos:
        return_path = path_avoiding_plots(garden, prev_pos, end_pos)
        for i in range(1, len(return_path)):
            prev = return_path[i - 1]
            cur = return_path[i]
            dr = cur[0] - prev[0]
            dc = cur[1] - prev[1]
            view = direction_view(dr, dc)
            t = _append_walk_segment(tl, prev, cur, view, t, timing, sprites)
            prev_pos = cur

    wait_x, wait_y = character_topleft(*cell_feet_xy(*end_pos))

    max_growth_end = t
    last_stage_dur = timing.growth_stage
    for (row, col), water_end in watered_at.items():
        plot = garden.plot_at(row, col)
        if plot is None:
            continue
        tier = plot.flower_tier
        base = water_end + timing.growth_stagger * (row + col) * 0.1
        gt = base
        last_stage_dur = timing.growth_stage
        for stage in range(1, 5):
            tl.growth.append(
                GrowthKeyframe(time=gt, row=row, col=col, tier=tier, stage=stage)
            )
            last_stage_dur = _random_growth_delay(timing)
            max_growth_end = max(max_growth_end, gt + last_stage_dur)
            gt += last_stage_dur

    wait_start = t
    wait_end = max_growth_end + last_stage_dur
    wi = 0
    wt = wait_start
    while wt < wait_end:
        tl.waiting.append(
            WaitingKeyframe(time=wt, x=wait_x, y=wait_y, frame_index=wi)
        )
        wi += 1
        wt += timing.waiting_loop

    feet_x, feet_y = cell_feet_xy(*end_pos)
    for i, emoji in enumerate(WAITING_EMOJIS):
        et = wait_start + i * (timing.emoji_float / len(WAITING_EMOJIS))
        tl.emojis.append(
            EmojiKeyframe(
                time=et,
                x=feet_x,
                y=feet_y - CHARACTER_HEIGHT,
                emoji=emoji,
                offset_y=-8 - (i % 3) * 8,
            )
        )

    tl.total_duration = wait_end + 1.0
    return tl
