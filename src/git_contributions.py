from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path


def _parse_git_log(repo: Path, since: date, until: date) -> dict[date, int]:
    """Conta commits por dia via git log."""
    cmd = [
        "git",
        "-C",
        str(repo),
        "log",
        f"--since={since.isoformat()}",
        f"--until={(until + timedelta(days=1)).isoformat()}",
        "--format=%ad",
        "--date=short",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"git log falhou: {result.stderr.strip() or 'repositório inválido?'}"
        )

    counts: dict[date, int] = defaultdict(int)
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        day = datetime.strptime(line, "%Y-%m-%d").date()
        counts[day] += 1
    return dict(counts)


def _github_grid_range(end: date | None = None) -> tuple[date, date]:
    """Intervalo de 53 semanas alinhado ao grid do GitHub (domingo → sábado)."""
    from .config import COLS

    if end is None:
        end = date.today()
    # Domingo da semana que contém `end`
    days_since_sunday = (end.weekday() + 1) % 7
    current_week_sunday = end - timedelta(days=days_since_sunday)
    start = current_week_sunday - timedelta(weeks=COLS - 1)
    grid_end = start + timedelta(days=COLS * 7 - 1)
    return start, grid_end


def load_contributions_from_git(repo: Path | None = None) -> dict[date, int]:
    repo = repo or Path.cwd()
    start, end = _github_grid_range()
    return _parse_git_log(repo, start, end)


def load_contributions_from_json(path: Path) -> dict[date, int]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {datetime.strptime(k, "%Y-%m-%d").date(): int(v) for k, v in raw.items()}


def contributions_to_grid(counts: dict[date, int], start: date, end: date) -> list[list[int]]:
    """Retorna matriz [row][col] com contagem de commits (7×53)."""
    from .config import COLS, ROWS

    grid = [[0] * COLS for _ in range(ROWS)]
    current = start
    col = 0
    while current <= end and col < COLS:
        for row in range(ROWS):
            d = current + timedelta(days=row)
            if d > end:
                break
            grid[row][col] = counts.get(d, 0)
        current += timedelta(days=7)
        col += 1
    return grid


def get_grid_dates(start: date | None = None, end: date | None = None) -> tuple[date, date]:
    if start is None or end is None:
        return _github_grid_range(end)
    return start, end
