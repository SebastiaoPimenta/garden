#!/usr/bin/env python3
"""CLI — Gera SVG animado do jardim a partir dos commits."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.garden import SpriteCatalog
from src.svg_builder import generate_svg, generate_svg_pair


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gera um SVG animado estilo contribution grid — jardim regado pela garota."
    )
    parser.add_argument(
        "-r",
        "--repo",
        type=Path,
        default=None,
        help="Repositório git (padrão: diretório atual)",
    )
    parser.add_argument(
        "-j",
        "--json",
        type=Path,
        default=None,
        help='JSON com contribuições {"YYYY-MM-DD": count, ...}',
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Gera só um SVG embutido neste caminho (padrão: dois arquivos em output/)",
    )
    parser.add_argument(
        "--check-sprites",
        action="store_true",
        help="Lista sprites ausentes e sai",
    )
    args = parser.parse_args(argv)

    if args.check_sprites:
        catalog = SpriteCatalog()
        missing = catalog.missing_character_report()
        if missing:
            print("Sprites ausentes (placeholders serão usados):")
            for m in missing:
                print(f"  - {m}")
        else:
            print("Todos os sprites obrigatórios encontrados!")
        return 0

    try:
        if args.output:
            out = generate_svg(
                repo=args.repo,
                output=args.output,
                json_input=args.json,
                embed_sprites=True,
            )
            print(f"SVG gerado: {out}")
        else:
            github, local = generate_svg_pair(
                repo=args.repo,
                json_input=args.json,
            )
            print(f"SVG GitHub (commitar): {github}")
            print(f"SVG local (abrir no navegador): {local}")
    except Exception as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1

    catalog = SpriteCatalog()
    missing = catalog.missing_character_report()
    if missing:
        print(f"\n{len(missing)} sprite(s) ausente(s) — usando placeholders.")
        print("Coloque seus PNG em sprites/ (veja sprites/README.md)")
        print("Execute: python -m src.main --check-sprites")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
