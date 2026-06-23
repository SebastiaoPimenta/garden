from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from .animator import AnimationTimeline
from .config import (
    CELL_GAP,
    CELL_SIZE,
    COLS,
    PADDING,
    ROWS,
    SOIL_COLORS,
    SPRITES_DIR,
    commits_to_soil_level,
)
from .garden import Garden, SpriteCatalog
from .git_contributions import contributions_to_grid, get_grid_dates, load_contributions_from_git


def _rel_sprite_path(path: Path, output: Path) -> str:
    try:
        return path.relative_to(output.parent).as_posix()
    except ValueError:
        return path.relative_to(SPRITES_DIR.parent).as_posix()


def _cell_xy(row: int, col: int) -> tuple[float, float]:
    x = PADDING + col * (CELL_SIZE + CELL_GAP)
    y = PADDING + row * (CELL_SIZE + CELL_GAP)
    return x, y


def _svg_size() -> tuple[int, int]:
    w = PADDING * 2 + COLS * CELL_SIZE + (COLS - 1) * CELL_GAP
    h = PADDING * 2 + ROWS * CELL_SIZE + (ROWS - 1) * CELL_GAP
    return w, h


def _prettify(elem: ET.Element) -> str:
    rough = ET.tostring(elem, encoding="unicode")
    return minidom.parseString(rough).toprettyxml(indent="  ")


class SvgBuilder:
    def __init__(
        self,
        garden: Garden,
        timeline: AnimationTimeline,
        sprites: SpriteCatalog | None = None,
        output_path: Path | None = None,
    ) -> None:
        self.garden = garden
        self.timeline = timeline
        self.sprites = sprites or SpriteCatalog()
        self.output_path = output_path
        self.width, self.height = _svg_size()
        self.duration = timeline.total_duration

    def build(self) -> str:
        svg = ET.Element(
            "svg",
            {
                "xmlns": "http://www.w3.org/2000/svg",
                "xmlns:xlink": "http://www.w3.org/1999/xlink",
                "width": str(self.width),
                "height": str(self.height),
                "viewBox": f"0 0 {self.width} {self.height}",
            },
        )

        # Fundo
        ET.SubElement(
            svg,
            "rect",
            {
                "width": "100%",
                "height": "100%",
                "fill": "#f6f8fa",
            },
        )

        defs = ET.SubElement(svg, "defs")
        self._define_soil_patterns(defs)
        self._define_sprite_symbols(defs)

        # Camada: terras
        soil_g = ET.SubElement(svg, "g", {"id": "soil-layer"})
        for r in range(self.garden.rows):
            for c in range(self.garden.cols):
                commits = self.garden.grid[r][c]
                self._draw_soil(soil_g, r, c, commits)

        # Camada: flores (crescem em estágios)
        flower_g = ET.SubElement(svg, "g", {"id": "flower-layer"})
        for gk in self.timeline.growth:
            self._draw_flower_stage(flower_g, gk)

        # Camada: personagem
        char_g = ET.SubElement(svg, "g", {"id": "character-layer"})
        self._draw_character(char_g)

        # Camada: emojis
        emoji_g = ET.SubElement(svg, "g", {"id": "emoji-layer"})
        self._draw_emojis(emoji_g)

        return _prettify(svg)

    def _define_soil_patterns(self, defs: ET.Element) -> None:
        for level, color in SOIL_COLORS.items():
            sprite = self.sprites.soil_sprite(level)
            if sprite and sprite.is_file():
                pat = ET.SubElement(
                    defs,
                    "pattern",
                    {
                        "id": f"soil-{level}",
                        "width": str(CELL_SIZE),
                        "height": str(CELL_SIZE),
                        "patternUnits": "userSpaceOnUse",
                    },
                )
                href = _rel_sprite_path(sprite, self.output_path) if self.output_path else sprite.as_posix()
                ET.SubElement(
                    pat,
                    "image",
                    {
                        "href": href,
                        "width": str(CELL_SIZE),
                        "height": str(CELL_SIZE),
                    },
                )

    def _define_sprite_symbols(self, defs: ET.Element) -> None:
        # Pré-carrega símbolos de sprites usados na animação
        seen: set[str] = set()

        def add_symbol(symbol_id: str, sprite_path: Path | None) -> None:
            if sprite_path is None or not sprite_path.is_file():
                return
            key = str(sprite_path)
            if key in seen:
                return
            seen.add(key)
            sym = ET.SubElement(
                defs,
                "symbol",
                {
                    "id": symbol_id,
                    "viewBox": f"0 0 {CELL_SIZE} {CELL_SIZE}",
                },
            )
            href = (
                _rel_sprite_path(sprite_path, self.output_path)
                if self.output_path
                else sprite_path.as_posix()
            )
            ET.SubElement(
                sym,
                "image",
                {
                    "href": href,
                    "width": str(CELL_SIZE),
                    "height": str(CELL_SIZE),
                },
            )

        for view in ("front", "back", "left", "right"):
            for action in ("idle", "walk", "watering"):
                frames = self.sprites.character_frames(view, action)
                for i, fp in enumerate(frames):
                    add_symbol(f"char-{view}-{action}-{i}", fp)

        for i, fp in enumerate(self.sprites.waiting_frames()):
            add_symbol(f"char-waiting-{i}", fp)

        for tier in range(1, 5):
            for stage in range(1, 5):
                add_symbol(
                    f"flower-t{tier}-s{stage}",
                    self.sprites.flower_sprite(tier, stage),
                )

    def _draw_soil(self, parent: ET.Element, row: int, col: int, commits: int) -> None:
        x, y = _cell_xy(row, col)
        level = commits_to_soil_level(commits)
        sprite = self.sprites.soil_sprite(level)
        attrs: dict[str, str] = {
            "x": str(x),
            "y": str(y),
            "width": str(CELL_SIZE),
            "height": str(CELL_SIZE),
            "rx": "2",
        }
        if sprite and sprite.is_file():
            attrs["fill"] = f"url(#soil-{level})"
            ET.SubElement(parent, "rect", attrs)
        else:
            attrs["fill"] = SOIL_COLORS.get(level, SOIL_COLORS[0])
            if level == 0:
                attrs["stroke"] = "#d0d7de"
                attrs["stroke-width"] = "0.5"
            ET.SubElement(parent, "rect", attrs)

    def _draw_flower_stage(self, parent: ET.Element, gk) -> None:
        x, y = _cell_xy(gk.row, gk.col)
        symbol_id = f"flower-t{gk.tier}-s{gk.stage}"
        sprite = self.sprites.flower_sprite(gk.tier, gk.stage)

        g = ET.SubElement(
            parent,
            "g",
            {
                "id": f"flower-{gk.row}-{gk.col}-s{gk.stage}",
                "opacity": "0",
            },
        )

        if sprite and sprite.is_file():
            use = ET.SubElement(
                g,
                "use",
                {
                    "href": f"#{symbol_id}",
                    "x": str(x),
                    "y": str(y),
                    "width": str(CELL_SIZE),
                    "height": str(CELL_SIZE),
                },
            )
        else:
            # Placeholder: círculo colorido por tier/estágio
            colors = {1: "#ffd93d", 2: "#ff6b9d", 3: "#c44569", 4: "#f8b500"}
            size = 2 + gk.stage * 2
            cx = x + CELL_SIZE / 2
            cy = y + CELL_SIZE / 2 - (4 - gk.stage)
            ET.SubElement(
                g,
                "circle",
                {
                    "cx": str(cx),
                    "cy": str(cy),
                    "r": str(size),
                    "fill": colors.get(gk.tier, "#40c463"),
                    "opacity": str(0.4 + gk.stage * 0.15),
                },
            )
            use = g  # para animate

        appear = gk.time
        disappear = appear + 999 if gk.stage == 4 else self._next_growth_time(gk)

        anim_in = ET.SubElement(
            g,
            "animate",
            {
                "attributeName": "opacity",
                "from": "0",
                "to": "1",
                "begin": f"{appear:.3f}s",
                "dur": "0.01s",
                "fill": "freeze",
            },
        )
        if gk.stage < 4:
            ET.SubElement(
                g,
                "animate",
                {
                    "attributeName": "opacity",
                    "from": "1",
                    "to": "0",
                    "begin": f"{disappear:.3f}s",
                    "dur": "0.01s",
                    "fill": "freeze",
                },
            )

    def _next_growth_time(self, gk) -> float:
        for other in self.timeline.growth:
            if (
                other.row == gk.row
                and other.col == gk.col
                and other.stage == gk.stage + 1
            ):
                return other.time
        return gk.time + 1.0

    def _draw_character(self, parent: ET.Element) -> None:
        char = ET.SubElement(parent, "g", {"id": "gardener"})

        # Combina walk + water + waiting em sequência de visibilidade
        all_frames: list[tuple[float, float, int, int, str, str, int]] = []

        for wk in self.timeline.walk:
            all_frames.append(
                (wk.time, wk.time + 0.001, wk.row, wk.col, wk.view, "walk", wk.frame_index)
            )

        for wk in self.timeline.water:
            all_frames.append(
                (
                    wk.time,
                    wk.time + 0.001,
                    wk.row,
                    wk.col,
                    wk.view,
                    "watering",
                    wk.frame_index,
                )
            )

        for wk in self.timeline.waiting:
            all_frames.append(
                (
                    wk.time,
                    wk.time + 0.001,
                    wk.row,
                    wk.col,
                    "front",
                    "waiting",
                    wk.frame_index,
                )
            )

        all_frames.sort(key=lambda f: f[0])

        for i, frame in enumerate(all_frames):
            t0, t1, row, col, view, action, fi = frame
            x, y = _cell_xy(row, col)
            g = ET.SubElement(char, "g", {"opacity": "0"})

            symbol = self._resolve_char_symbol(view, action, fi)
            if symbol:
                ET.SubElement(
                    g,
                    "use",
                    {
                        "href": f"#{symbol}",
                        "x": str(x),
                        "y": str(y),
                        "width": str(CELL_SIZE),
                        "height": str(CELL_SIZE),
                    },
                )
            else:
                self._draw_char_placeholder(g, x, y, view, action)

            begin = f"{t0:.3f}s"
            ET.SubElement(
                g,
                "animate",
                {
                    "attributeName": "opacity",
                    "from": "0",
                    "to": "1",
                    "begin": begin,
                    "dur": "0.001s",
                    "fill": "freeze",
                },
            )
            if i + 1 < len(all_frames):
                next_t = all_frames[i + 1][0]
                ET.SubElement(
                    g,
                    "animate",
                    {
                        "attributeName": "opacity",
                        "from": "1",
                        "to": "0",
                        "begin": f"{next_t:.3f}s",
                        "dur": "0.001s",
                        "fill": "freeze",
                    },
                )
            else:
                ET.SubElement(
                    g,
                    "animate",
                    {
                        "attributeName": "opacity",
                        "values": "1;1",
                        "begin": begin,
                        "dur": f"{self.duration:.3f}s",
                        "fill": "freeze",
                    },
                )

    def _resolve_char_symbol(self, view: str, action: str, frame_index: int) -> str | None:
        if action == "waiting":
            frames = self.sprites.waiting_frames()
            if not frames:
                frames = self.sprites.character_frames("front", "idle")
            if not frames:
                return None
            fi = frame_index % len(frames)
            return f"char-waiting-{fi}" if self.sprites.waiting_frames() else f"char-front-idle-0"

        frames = self.sprites.character_frames(view, action)
        if not frames:
            # fallback: idle da mesma view
            frames = self.sprites.character_frames(view, "idle")
        if not frames:
            return None
        fi = frame_index % len(frames)
        return f"char-{view}-{action}-{fi}"

    def _draw_char_placeholder(
        self, parent: ET.Element, x: float, y: float, view: str, action: str
    ) -> None:
        body = "#ff9ebb"
        hair = "#5c4033"
        ET.SubElement(
            parent,
            "rect",
            {"x": str(x + 4), "y": str(y + 6), "width": "8", "height": "8", "fill": body},
        )
        ET.SubElement(
            parent,
            "rect",
            {"x": str(x + 3), "y": str(y + 2), "width": "10", "height": "5", "fill": hair},
        )
        if action == "watering":
            ET.SubElement(
                parent,
                "rect",
                {
                    "x": str(x + 10),
                    "y": str(y + 8),
                    "width": "4",
                    "height": "3",
                    "fill": "#6cb4ee",
                },
            )

    def _draw_emojis(self, parent: ET.Element) -> None:
        wait_start = self.timeline.waiting[0].time if self.timeline.waiting else self.duration
        for ek in self.timeline.emojis:
            x, y = _cell_xy(ek.row, ek.col)
            text = ET.SubElement(
                parent,
                "text",
                {
                    "x": str(x + CELL_SIZE / 2),
                    "y": str(y + ek.offset_y),
                    "text-anchor": "middle",
                    "font-size": "10",
                    "opacity": "0",
                },
            )
            text.text = ek.emoji

            ET.SubElement(
                text,
                "animate",
                {
                    "attributeName": "opacity",
                    "values": "0;1;1;0",
                    "keyTimes": "0;0.1;0.8;1",
                    "begin": f"{ek.time:.3f}s",
                    "dur": "2s",
                    "repeatCount": "indefinite",
                },
            )
            ET.SubElement(
                text,
                "animateTransform",
                {
                    "attributeName": "transform",
                    "type": "translate",
                    "values": f"0 0; 0 -6; 0 -12",
                    "begin": f"{ek.time:.3f}s",
                    "dur": "2s",
                    "repeatCount": "indefinite",
                },
            )


def generate_svg(
    repo: Path | None = None,
    output: Path | None = None,
    json_input: Path | None = None,
) -> Path:
    from .animator import build_timeline

    if json_input:
        from .git_contributions import load_contributions_from_json

        counts = load_contributions_from_json(json_input)
        start, end = get_grid_dates()
    else:
        counts = load_contributions_from_git(repo)
        start, end = get_grid_dates()

    grid = contributions_to_grid(counts, start, end)
    garden = Garden(grid=grid)
    timeline = build_timeline(garden)
    sprites = SpriteCatalog()

    out = output or Path(__file__).resolve().parent.parent / "output" / "garden-contribution.svg"
    out.parent.mkdir(parents=True, exist_ok=True)

    builder = SvgBuilder(garden, timeline, sprites, out)
    svg_content = builder.build()
    out.write_text(svg_content, encoding="utf-8")
    return out
