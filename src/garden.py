from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import (
    CHARACTER_ACTIONS,
    CHARACTER_VIEWS,
    SPRITES_DIR,
    commits_to_soil_level,
    commits_to_tier,
)


@dataclass(frozen=True)
class Plot:
    row: int
    col: int
    commits: int

    @property
    def soil_level(self) -> int:
        return commits_to_soil_level(self.commits)

    @property
    def flower_tier(self) -> int:
        return commits_to_tier(self.commits)

    @property
    def key(self) -> tuple[int, int]:
        return (self.row, self.col)


@dataclass
class Garden:
    grid: list[list[int]]

    @property
    def rows(self) -> int:
        return len(self.grid)

    @property
    def cols(self) -> int:
        return len(self.grid[0]) if self.grid else 0

    def plots_to_water(self) -> list[Plot]:
        plots: list[Plot] = []
        for r, row in enumerate(self.grid):
            for c, commits in enumerate(row):
                if commits > 0:
                    plots.append(Plot(row=r, col=c, commits=commits))
        return plots

    def plot_at(self, row: int, col: int) -> Plot | None:
        if 0 <= row < self.rows and 0 <= col < self.cols:
            commits = self.grid[row][col]
            if commits > 0:
                return Plot(row=row, col=col, commits=commits)
        return None


def _sorted_pngs(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(folder.glob("*.png"))


class SpriteCatalog:
    """Carrega caminhos de sprites PNG existentes."""

    def __init__(self, root: Path = SPRITES_DIR) -> None:
        self.root = root

    def character_frames(self, view: str, action: str) -> list[Path]:
        return _sorted_pngs(self.root / "character" / view / action)

    def waiting_frames(self) -> list[Path]:
        return _sorted_pngs(self.root / "character" / "waiting")

    def flower_sprite(self, tier: int, stage: int) -> Path | None:
        path = self.root / "flowers" / f"tier-{tier}" / f"stage-{stage}.png"
        return path if path.is_file() else None

    def soil_sprite(self, level: int) -> Path | None:
        path = self.root / "soil" / f"level-{level}.png"
        return path if path.is_file() else None

    def has_character(self, view: str, action: str) -> bool:
        return bool(self.character_frames(view, action))

    def missing_character_report(self) -> list[str]:
        missing: list[str] = []
        for view in CHARACTER_VIEWS:
            for action in CHARACTER_ACTIONS:
                if not self.has_character(view, action):
                    missing.append(f"character/{view}/{action}/")
        if not self.waiting_frames():
            missing.append("character/waiting/")
        for tier in range(1, 5):
            for stage in range(1, 5):
                if self.flower_sprite(tier, stage) is None:
                    missing.append(f"flowers/tier-{tier}/stage-{stage}.png")
        return missing
