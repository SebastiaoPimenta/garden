from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Grid no estilo GitHub: 7 linhas (dias da semana) × ~53 colunas (semanas)
ROWS = 7
COLS = 53

CELL_SIZE = 32
CELL_GAP = 12
PADDING = 16

# Personagem maior que a célula — pés ancorados no centro-inferior do plot
CHARACTER_WIDTH = 48
CHARACTER_HEIGHT = 65
CHARACTER_OVERFLOW_TOP = max(0, CHARACTER_HEIGHT - CELL_SIZE)

# Flores maiores que a célula — base ancorada no centro-inferior do plot
FLOWER_WIDTH = 64
FLOWER_HEIGHT = 64
FLOWER_OVERFLOW_TOP = max(0, FLOWER_HEIGHT - CELL_SIZE)
GRID_OVERFLOW_TOP = max(CHARACTER_OVERFLOW_TOP, FLOWER_OVERFLOW_TOP)

# Posição inicial e final do personagem no grid (row, col)
HOME_POSITION = (0, 0)

# Cores de terra por nível de contribuição (fallback sem sprite)
SOIL_COLORS = {
    0: "#ebedf0",  # grama / vazio
    1: "#9be9a8",
    2: "#40c463",
    3: "#30a14e",
    4: "#216e39",
}

# Mapeamento commits → tier de flor (1–4)
def commits_to_tier(count: int) -> int:
    if count <= 0:
        return 0
    if count == 1:
        return 1
    if count == 2:
        return 2
    if count == 3:
        return 3
    return 4


def commits_to_soil_level(count: int) -> int:
    if count <= 0:
        return 0
    return min(count, 4)


@dataclass(frozen=True)
class Timing:
    """Duração de cada fase da animação (segundos)."""

    walk_step_duration: float = 0.4
    walk_substeps: int = 4
    idle_before_water: float = 0.2
    water_frame: float = 0.15
    growth_stage: float = 1.0
    growth_stage_min: float = 1.0
    growth_stage_max: float = 10.0
    growth_stagger: float = 0.15
    waiting_loop: float = 0.5
    emoji_float: float = 2.0


TIMING = Timing()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPRITES_DIR = PROJECT_ROOT / "sprites"
OUTPUT_DIR = PROJECT_ROOT / "output"

CHARACTER_VIEWS = ("front", "back", "left", "right")
CHARACTER_ACTIONS = ("idle", "walk", "watering")
