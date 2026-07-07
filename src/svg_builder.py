from __future__ import annotations

import base64
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from .animator import AnimationTimeline
from .config import (
    CELL_SIZE,
    CHARACTER_HEIGHT,
    CHARACTER_WIDTH,
    FLOWER_HEIGHT,
    FLOWER_WIDTH,
    SOIL_COLORS,
    commits_to_soil_level,
)
from .garden import Garden, SpriteCatalog
from .git_contributions import contributions_to_grid, get_grid_dates, load_contributions_from_git
from .positions import cell_xy, flower_topleft_at_cell, svg_size

XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


def _embed_sprite_href(path: Path, cache: dict[str, str]) -> str | None:
    key = str(path.resolve())
    if key in cache:
        return cache[key]
    if not path.is_file():
        return None
    data = path.read_bytes()
    mime = "image/png"
    if data[:3] == b"GIF":
        mime = "image/gif"
    elif data[:2] == b"\xff\xd8":
        mime = "image/jpeg"
    cache[key] = f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"
    return cache[key]


def _prettify(elem: ET.Element) -> str:
    rough = ET.tostring(elem, encoding="unicode")
    return minidom.parseString(rough).toprettyxml(indent="  ")


class SvgBuilder:
    def __init__(
        self,
        garden: Garden,
        timeline: AnimationTimeline,
        sprites: SpriteCatalog | None = None,
    ) -> None:
        self.garden = garden
        self.timeline = timeline
        self.sprites = sprites or SpriteCatalog()
        self.width, self.height = svg_size()
        self.duration = timeline.total_duration
        self._embed_cache: dict[str, str] = {}
        self._defs_root: ET.Element | None = None
        self._sprite_defs: dict[str, str] = {}

    def _register_defs(self, defs: ET.Element) -> None:
        self._defs_root = defs

    def _sprite_href(self, sprite_path: Path) -> str | None:
        if not sprite_path.is_file():
            return None
        return _embed_sprite_href(sprite_path, self._embed_cache)

    def _sprite_def_id(self, sprite_path: Path, width: int, height: int) -> str | None:
        if self._defs_root is None:
            return None
        key = f"{sprite_path.resolve()}:{width}x{height}"
        if key in self._sprite_defs:
            return self._sprite_defs[key]
        href = self._sprite_href(sprite_path)
        if href is None:
            return None
        def_id = f"img-{len(self._sprite_defs)}"
        ET.SubElement(
            self._defs_root,
            "image",
            {
                "id": def_id,
                "href": href,
                XLINK_HREF: href,
                "width": str(width),
                "height": str(height),
            },
        )
        self._sprite_defs[key] = def_id
        return def_id

    def _sprite_image(
        self,
        parent: ET.Element,
        sprite_path: Path | None,
        x: float,
        y: float,
        width: int,
        height: int,
    ) -> bool:
        if sprite_path is None:
            return False
        def_id = self._sprite_def_id(sprite_path, width, height)
        if def_id is None:
            return False
        ref = f"#{def_id}"
        ET.SubElement(
            parent,
            "use",
            {
                "href": ref,
                XLINK_HREF: ref,
                "x": str(x),
                "y": str(y),
                "width": str(width),
                "height": str(height),
            },
        )
        return True

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

        ET.SubElement(
            svg,
            "rect",
            {"width": "100%", "height": "100%", "fill": "#f6f8fa"},
        )

        defs = ET.SubElement(svg, "defs")
        self._register_defs(defs)

        soil_g = ET.SubElement(svg, "g", {"id": "soil-layer"})
        for r in range(self.garden.rows):
            for c in range(self.garden.cols):
                self._draw_soil(soil_g, r, c, self.garden.grid[r][c])

        flower_g = ET.SubElement(svg, "g", {"id": "flower-layer"})
        growth_sorted = sorted(
            self.timeline.growth, key=lambda gk: (gk.row, gk.col, gk.stage)
        )
        for gk in growth_sorted:
            self._draw_flower_stage(flower_g, gk)

        char_g = ET.SubElement(svg, "g", {"id": "character-layer"})
        self._draw_character(char_g)

        emoji_g = ET.SubElement(svg, "g", {"id": "emoji-layer"})
        self._draw_emojis(emoji_g)

        return _prettify(svg)

    def _draw_soil(self, parent: ET.Element, row: int, col: int, commits: int) -> None:
        x, y = cell_xy(row, col)
        level = commits_to_soil_level(commits)
        sprite = self.sprites.soil_sprite(level)
        if sprite and sprite.is_file():
            if not self._sprite_image(parent, sprite, x, y, CELL_SIZE, CELL_SIZE):
                self._draw_soil_rect(parent, x, y, level)
        else:
            self._draw_soil_rect(parent, x, y, level)

    def _draw_soil_rect(
        self, parent: ET.Element, x: float, y: float, level: int
    ) -> None:
        attrs: dict[str, str] = {
            "x": str(x),
            "y": str(y),
            "width": str(CELL_SIZE),
            "height": str(CELL_SIZE),
            "rx": "4",
            "fill": SOIL_COLORS.get(level, SOIL_COLORS[0]),
        }
        if level == 0:
            attrs["stroke"] = "#d0d7de"
            attrs["stroke-width"] = "0.5"
        ET.SubElement(parent, "rect", attrs)

    def _draw_flower_stage(self, parent: ET.Element, gk) -> None:
        fx, fy = flower_topleft_at_cell(gk.row, gk.col)
        sprite = self.sprites.flower_sprite(gk.tier, gk.stage)

        g = ET.SubElement(
            parent,
            "g",
            {"id": f"flower-{gk.row}-{gk.col}-s{gk.stage}", "opacity": "0"},
        )

        if not self._sprite_image(g, sprite, fx, fy, FLOWER_WIDTH, FLOWER_HEIGHT):
            colors = {1: "#ffd93d", 2: "#ff6b9d", 3: "#c44569", 4: "#f8b500"}
            cx, cy = flower_topleft_at_cell(gk.row, gk.col)
            cx += FLOWER_WIDTH / 2
            cy += FLOWER_HEIGHT - 4 - (4 - gk.stage) * 4
            size = 4 + gk.stage * 6
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

        appear = gk.time
        disappear = appear + 999 if gk.stage == 4 else self._next_growth_time(gk)

        ET.SubElement(
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

        all_frames: list[tuple[float, float, float, str, str, int]] = []

        for wk in self.timeline.walk:
            all_frames.append((wk.time, wk.x, wk.y, wk.view, "walk", wk.frame_index))

        for ik in self.timeline.idle:
            all_frames.append((ik.time, ik.x, ik.y, ik.view, "idle", ik.frame_index))

        for wk in self.timeline.water:
            all_frames.append(
                (wk.time, wk.x, wk.y, wk.view, "watering", wk.frame_index)
            )

        for wk in self.timeline.waiting:
            all_frames.append(
                (wk.time, wk.x, wk.y, "front", "waiting", wk.frame_index)
            )

        all_frames.sort(key=lambda f: f[0])

        for i, frame in enumerate(all_frames):
            t0, x, y, view, action, fi = frame
            g = ET.SubElement(char, "g", {"opacity": "0"})

            symbol = self._resolve_char_sprite(view, action, fi)
            if not self._sprite_image(
                g, symbol, x, y, CHARACTER_WIDTH, CHARACTER_HEIGHT
            ):
                self._draw_char_placeholder(g, x, y, action)

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

    def _resolve_char_sprite(
        self, view: str, action: str, frame_index: int
    ) -> Path | None:
        if action == "waiting":
            waiting = self.sprites.waiting_frames()
            if waiting:
                return waiting[frame_index % len(waiting)]
            frames = self.sprites.character_frames("front", "idle")
            return frames[0] if frames else None

        if action == "idle":
            frames = self.sprites.character_frames(view, "idle")
            return frames[frame_index % len(frames)] if frames else None

        frames = self.sprites.character_frames(view, action)
        if not frames:
            frames = self.sprites.character_frames(view, "idle")
        if not frames:
            return None
        return frames[frame_index % len(frames)]

    def _draw_char_placeholder(
        self, parent: ET.Element, x: float, y: float, action: str
    ) -> None:
        body = "#ff9ebb"
        hair = "#5c4033"
        h = CHARACTER_HEIGHT
        w = CHARACTER_WIDTH
        # Corpo proporcional à altura maior
        ET.SubElement(
            parent,
            "rect",
            {
                "x": str(x + w * 0.25),
                "y": str(y + h * 0.45),
                "width": str(w * 0.5),
                "height": str(h * 0.35),
                "fill": body,
            },
        )
        ET.SubElement(
            parent,
            "rect",
            {
                "x": str(x + w * 0.2),
                "y": str(y + h * 0.15),
                "width": str(w * 0.6),
                "height": str(h * 0.22),
                "fill": hair,
            },
        )
        ET.SubElement(
            parent,
            "rect",
            {
                "x": str(x + w * 0.35),
                "y": str(y + h * 0.8),
                "width": str(w * 0.12),
                "height": str(h * 0.2),
                "fill": body,
            },
        )
        ET.SubElement(
            parent,
            "rect",
            {
                "x": str(x + w * 0.53),
                "y": str(y + h * 0.8),
                "width": str(w * 0.12),
                "height": str(h * 0.2),
                "fill": body,
            },
        )
        if action == "watering":
            ET.SubElement(
                parent,
                "rect",
                {
                    "x": str(x + w * 0.65),
                    "y": str(y + h * 0.5),
                    "width": str(w * 0.25),
                    "height": str(h * 0.12),
                    "fill": "#6cb4ee",
                },
            )
        if action == "walk":
            # Pequeno deslocamento do pé para sugerir passo
            leg = parent.findall("rect")[-2]
            leg.set("y", str(float(leg.get("y", y)) + 2))

    def _draw_emojis(self, parent: ET.Element) -> None:
        for ek in self.timeline.emojis:
            text = ET.SubElement(
                parent,
                "text",
                {
                    "x": str(ek.x),
                    "y": str(ek.y + ek.offset_y),
                    "text-anchor": "middle",
                    "font-size": "18",
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
                    "values": "0 0; 0 -12; 0 -24",
                    "begin": f"{ek.time:.3f}s",
                    "dur": "2s",
                    "repeatCount": "indefinite",
                },
            )


def _load_garden_timeline(
    repo: Path | None = None,
    json_input: Path | None = None,
) -> tuple[Garden, AnimationTimeline, SpriteCatalog]:
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
    sprites = SpriteCatalog()
    timeline = build_timeline(garden, sprites=sprites)
    return garden, timeline, sprites


_PREVIEW_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Garden Contribution Grid</title>
  <style>
    html, body {{ margin: 0; min-height: 100%; background: #f6f8fa; }}
    body {{
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
      box-sizing: border-box;
    }}
    object {{ max-width: 100%; height: auto; border: 0; }}
  </style>
</head>
<body>
  <object data="{svg_name}" type="image/svg+xml">
    <p>Abra <a href="{svg_name}">{svg_name}</a> no navegador.</p>
  </object>
</body>
</html>
"""


def _write_preview_html(svg_path: Path) -> Path:
    preview = svg_path.parent / "preview.html"
    preview.write_text(
        _PREVIEW_HTML.format(svg_name=svg_path.name),
        encoding="utf-8",
    )
    return preview


def generate_svg(
    repo: Path | None = None,
    output: Path | None = None,
    json_input: Path | None = None,
) -> Path:
    garden, timeline, sprites = _load_garden_timeline(repo, json_input)

    out = (
        output
        or Path(__file__).resolve().parent.parent / "output" / "garden-contribution.svg"
    )
    out.parent.mkdir(parents=True, exist_ok=True)

    builder = SvgBuilder(garden, timeline, sprites)
    out.write_text(builder.build(), encoding="utf-8")
    _write_preview_html(out)
    return out
