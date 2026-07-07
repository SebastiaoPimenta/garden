# Sprites — Garden Contribution Grid

Sprites em **PNG** com fundo transparente. Todos os arquivos seguem convenções de nome para o gerador encontrá-los automaticamente.

## Dimensões recomendadas

| Tipo | Tamanho | Notas |
|------|---------|-------|
| Personagem | **48×65 px** | Pixel art; pés no centro-inferior da célula; corpo ultrapassa o plot |
| Flor (cada estágio) | **64×64 px** | Base no centro-inferior do plot; pode sobrepor células vizinhas |
| Terra | 32×32 px | Opcional; o gerador desenha cores se ausente |
| Efeitos | 32×32 px | Gotas, brilhos, etc. |

## Estrutura

```
sprites/
├── character/
│   ├── front/          # Vista frontal
│   ├── back/           # Vista de costas
│   ├── left/           # Perfil esquerdo
│   ├── right/          # Perfil direito
│   └── waiting/        # Poses extras pós-rega (ver abaixo)
├── flowers/
│   ├── tier-1/         # Terra pouco fértil (1 commit)
│   ├── tier-2/         # 2 commits
│   ├── tier-3/         # 3 commits
│   └── tier-4/         # Terra mais fértil (4+ commits)
├── soil/               # Opcional — texturas de terra por nível
└── effects/            # Opcional — gotas, partículas
```

## Personagem (`character/`)

Cada view (`front`, `back`, `left`, `right`) contém três pastas de ação:

```
character/{view}/{action}/{frame}.png
```

### Ações

| Pasta | Descrição | Frames |
|-------|-----------|--------|
| `idle/` | Parada | `000.png` (mínimo 1) |
| `walk/` | Caminhando | `000.png`, `001.png`, … (**mínimo 4** para passo fluido) |
| `watering/` | Regando | `000.png`, `001.png`, … (mínimo 2) |

**Views:** `front` · `back` · `left` · `right`

Sprites do personagem são **mais altos que a célula** (48×65 px). Desenhe com os **pés na linha inferior** do canvas — o gerador ancora os pés no centro-inferior de cada plot.

O gerador escolhe a view pela direção do movimento:
- Indo para cima → `back`
- Indo para baixo → `front`
- Indo para esquerda → `left`
- Indo para direita → `right`

### Poses de espera (`character/waiting/`)

Sprites extras usados quando a garota terminou de regar e aguarda as flores brotarem.

```
character/waiting/{frame}.png
```

Sugestão: 2–4 frames em loop (ex.: respirando, olhando em volta, segurando regador).

## Flores (`flowers/tier-{1-4}/`)

Cada tier representa a beleza da flor conforme a fertilidade da terra (intensidade do commit).

```
flowers/tier-{1-4}/stage-{1-4}.png
```

Sprites **64×64 px**, com a **base do caule no centro-inferior** do canvas. Flores maiores que o plot (32×32) e podem sobrepor plots adjacentes.

| Arquivo | Estágio |
|---------|---------|
| `stage-1.png` | Broto / semente |
| `stage-2.png` | Caule pequeno |
| `stage-3.png` | Botão |
| `stage-4.png` | Flor completa |

**Tiers:**
- `tier-1` — flor simples (ex.: margarida)
- `tier-2` — flor média (ex.: tulipa)
- `tier-3` — flor bonita (ex.: rosa)
- `tier-4` — flor exuberante (ex.: girassol, orquídea)

## Terra (`soil/`) — opcional

```
soil/level-{0-4}.png
```

| Nível | Commits no dia |
|-------|----------------|
| 0 | 0 (grama, sem plot) |
| 1 | 1 |
| 2 | 2 |
| 3 | 3 |
| 4 | 4+ |

Se ausente, o gerador usa cores sólidas.

## Efeitos (`effects/`) — opcional

```
effects/water-splash.png
effects/sparkle.png
```

## Checklist mínimo para animação completa

- [ ] `character/front/idle/000.png`
- [ ] `character/front/walk/000.png` + `001.png`
- [ ] `character/front/watering/000.png` + `001.png`
- [ ] Repetir para `back`, `left`, `right`
- [ ] `character/waiting/000.png` (+ frames extras)
- [ ] `flowers/tier-1/stage-1.png` … `stage-4.png` (repetir tiers 2–4)
