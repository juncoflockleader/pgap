# pgap-2d — Procedural 2D Asset Pipeline

Deterministic, offline generator for **stylized 2D game art**: anime-style
"monster girl" bust portraits and layered battle backdrops, written as PNG by a
stdlib encoder (no PIL). Pure Python + numpy, same architecture as every pgap
pipeline: spec → seeded `PCG64` RNG → module graph → render → file + manifest.

The 2D thesis is the same as 3d-actor's, but the ceiling is closer: stylization
is the *norm* in 2D, so algorithmic composition (part libraries, palettes,
soft-raster primitives) reads as intentional art direction rather than
programmer art.

## Usage

```bash
python pgap.py 2d --capabilities
python pgap.py 2d --kind portrait --archetype slime --seed 3 --out out
python pgap.py 2d --kind background --biome meadow --seed 1 --out out
python pgap.py 2d --spec my_spec.json --out out
```

## Capabilities

- **portrait** — archetypes: `slime`, `bat`, `wolf`, `human`. Seeded variation:
  hue jitter, eye color, blush intensity, ear/wing tilt, accessory
  (flower / sparkle / none). Output 512×512 RGBA (64..2048).
- **background** — biomes: `meadow`, `forest`, `cave`, `night`. Layer stack:
  sky gradient → sun/moon/stars → 3 smoothed random-walk ridge silhouettes →
  ground band → biome accents (flowers / tree silhouettes / glowing crystals /
  craters) → vignette. Output 1152×648 RGBA by default.

Validation is fail-closed: unknown kinds/archetypes/biomes/fields are rejected
with errors, never guessed.

## Output + handoff

Each run writes `<name>.png` plus `<name>.manifest.json` with role-tagged files
(`Portrait` / `BattleBackdrop`). The Godot last mile is plain file copying —
`.tscn`/`.tres` are text, so no bridge server is needed; for Unreal the usual
`unreal-mcp-rx` import path applies.

## Tests

```bash
python -m pytest tests/ -q        # from pgap-2d/
```
