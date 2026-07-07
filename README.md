# Garden Contribution Grid

Gerador de **SVG animado** para usar como contribution grid do GitHub — um jardim onde cada quadrado de commit é uma terra, regada por uma garotinha com regador. Quanto mais commits no dia, mais fértil a terra e mais bonita a flor que brota.

Inspirado nos grids animados (cobrinha, etc.), mas com vibe **Bomberman**: personagem em pixel art, caminhando pela grade e regando cada plot uma vez.

## Como funciona

1. **Commits → terras** — cada célula do grid (7 dias × 53 semanas) representa um dia; a intensidade da cor indica fertilidade (0–4+ commits).
2. **Garota jardineira** — percorre todas as terras com commits, uma a uma, e rega cada uma só uma vez.
3. **Flores em 4 estágios** — após regar, brotam em estágios; o tipo de flor depende do tier de fertilidade.
4. **Final** — personagem para e espera tudo florescer, com emojis ❤️ 💻 ✨ flutuando acima.

## Demonstração

<p align="center">
  <a href="https://SebastiaoPimenta.github.io/garden/">
    <strong>Clique para ver a animação em tela cheia</strong>
  </a>
</p>

<p align="center">
  <a href="https://SebastiaoPimenta.github.io/garden/">
    <img src="output/garden-contribution.svg" alt="Garden contribution grid animado" width="1200" />
  </a>
</p>

<p align="center"><sub>Prévia no README — o link acima abre a animação via GitHub Pages.</sub></p>

## Início rápido

```bash
# Gera output/garden-contribution.svg, output/preview.html e docs/index.html (GitHub Pages)
python3 -m src.main

# Caminho customizado (preview.html na mesma pasta)
python3 -m src.main -o output/meu-jardim.svg

# A partir de JSON (útil para testar)
python3 -m src.main -j examples/sample-contributions.json

# Verificar sprites faltando
python3 -m src.main --check-sprites
```

## Sprites (PNG)

Coloque seus sprites em `sprites/`. Convenção completa em [`sprites/README.md`](sprites/README.md).

```
sprites/
├── character/
│   ├── front/   back/   left/   right/
│   │   └── idle/   walk/   watering/   → 000.png, 001.png …
│   └── waiting/                         → poses pós-rega
├── flowers/
│   └── tier-1 … tier-4/
│       └── stage-1.png … stage-4.png
├── soil/          (opcional)
└── effects/       (opcional)
```

**Personagem:** 48×65 px (pés embaixo), 4 views × 3 ações (+ múltiplos frames em `walk/`).

**Flores:** 4 tiers (beleza) × 4 estágios (crescimento).

Sem sprites, o gerador usa **placeholders** coloridos para você visualizar a animação enquanto desenha os PNGs.

## Uso no GitHub

1. Gere os arquivos: `python3 -m src.main`
2. Faça commit de `output/garden-contribution.svg`, `output/preview.html` e `docs/`
3. Ative **GitHub Pages**: *Settings → Pages → Build from branch `main`, folder `/docs`*
4. A animação em tela cheia fica em `https://SEU_USUARIO.github.io/garden/`

Para usar em outro repo, ajuste o usuário na URL:

```html
<p align="center">
  <a href="https://SEU_USUARIO.github.io/garden/">
    <strong>Ver animação em tela cheia</strong>
  </a>
</p>
<p align="center">
  <a href="https://SEU_USUARIO.github.io/garden/">
    <img src="output/garden-contribution.svg" alt="Garden" width="1200" />
  </a>
</p>
```

> Links `raw.githubusercontent.com` exibem HTML como código-fonte. Use GitHub Pages (`docs/index.html`) ou abra `output/preview.html` localmente.

## Estrutura do projeto

```
garden/
├── sprites/          # seus PNGs aqui
├── src/
│   ├── config.py     # grid, cores, timing
│   ├── git_contributions.py
│   ├── garden.py
│   ├── pathfinding.py
│   ├── animator.py
│   ├── svg_builder.py
│   └── main.py
├── examples/
│   └── sample-contributions.json
└── output/           # SVG gerado
```

## Personalização

Edite `src/config.py` para ajustar:

- `CELL_SIZE` / `CELL_GAP` — tamanho das células
- `SOIL_COLORS` — cores fallback das terras
- `TIMING` — velocidade de caminhada, rega, crescimento e emojis

## Licença

MIT — use e adapte como quiser.
