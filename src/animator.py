from __future__ import annotations

from dataclasses import dataclass, field

from .config import TIMING
from .garden import Garden, Plot
from .pathfinding import expand_route, greedy_visit_order


@dataclass
class WalkKeyframe:
    time: float
    row: int
    col: int
    view: str
    frame_index: int


@dataclass
class WaterKeyframe:
    time: float
    row: int
    col: int
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
    row: int
    col: int
    frame_index: int


@dataclass
class EmojiKeyframe:
    time: float
    row: int
    col: int
    emoji: str
    offset_y: float = 0.0


@dataclass
class AnimationTimeline:
    walk: list[WalkKeyframe] = field(default_factory=list)
    water: list[WaterKeyframe] = field(default_factory=list)
    growth: list[GrowthKeyframe] = field(default_factory=list)
    waiting: list[WaitingKeyframe] = field(default_factory=list)
    emojis: list[EmojiKeyframe] = field(default_factory=list)
    total_duration: float = 0.0

    @property
    def watered_plots(self) -> list[tuple[int, int]]:
        return sorted({(w.row, w.col) for w in self.water})


WAITING_EMOJIS = ["❤️", "💻", "👩‍💻", "✨", "🌸", "💖", "🧑‍💻", "💚"]


def build_timeline(
    garden: Garden,
    start_pos: tuple[int, int] | None = None,
    timing=TIMING,
) -> AnimationTimeline:
    plots = garden.plots_to_water()
    order = greedy_visit_order(plots, start_pos)

    if start_pos is None:
        if order:
            start_pos = (order[0].row, order[0].col)
        else:
            start_pos = (garden.rows // 2, garden.cols // 2)

    route = expand_route(order, start_pos)
    tl = AnimationTimeline()
    t = 0.0
    walk_frame_counter: dict[str, int] = {}

    watered_at: dict[tuple[int, int], float] = {}

    for kind, pos, view in route:
        row, col = pos
        if kind == "walk":
            walk_frame_counter[view] = walk_frame_counter.get(view, 0)
            tl.walk.append(
                WalkKeyframe(
                    time=t,
                    row=row,
                    col=col,
                    view=view,
                    frame_index=walk_frame_counter[view],
                )
            )
            walk_frame_counter[view] += 1
            t += timing.walk_frame
        else:
            plot = garden.plot_at(row, col)
            if plot is None:
                continue
            for fi in range(3):  # 3 frames de rega
                tl.water.append(
                    WaterKeyframe(
                        time=t,
                        row=row,
                        col=col,
                        view=view,
                        frame_index=fi,
                        plot=plot,
                    )
                )
                t += timing.water_frame
            watered_at[(row, col)] = t

    # Posição de espera: último plot regado ou centro
    if order:
        wait_row, wait_col = order[-1].row, order[-1].col
    else:
        wait_row, wait_col = start_pos

    # Flores brotam em 4 estágios após cada rega
    max_growth_end = t
    for (row, col), water_end in watered_at.items():
        plot = garden.plot_at(row, col)
        if plot is None:
            continue
        tier = plot.flower_tier
        base = water_end + timing.growth_stagger * (row + col) * 0.1
        for stage in range(1, 5):
            gt = base + (stage - 1) * timing.growth_stage
            tl.growth.append(
                GrowthKeyframe(time=gt, row=row, col=col, tier=tier, stage=stage)
            )
            max_growth_end = max(max_growth_end, gt + timing.growth_stage)

    # Espera com emojis
    wait_start = t
    wait_end = max_growth_end + timing.growth_stage
    wi = 0
    wt = wait_start
    while wt < wait_end:
        tl.waiting.append(
            WaitingKeyframe(time=wt, row=wait_row, col=wait_col, frame_index=wi)
        )
        wi += 1
        wt += timing.waiting_loop

    for i, emoji in enumerate(WAITING_EMOJIS):
        et = wait_start + i * (timing.emoji_float / len(WAITING_EMOJIS))
        tl.emojis.append(
            EmojiKeyframe(
                time=et,
                row=wait_row,
                col=wait_col,
                emoji=emoji,
                offset_y=-8 - (i % 3) * 4,
            )
        )

    tl.total_duration = wait_end + 1.0
    return tl
