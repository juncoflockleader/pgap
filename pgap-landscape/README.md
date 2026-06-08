# pgap-landscape (psl) — Procedural Landscape Pipeline

Deterministic, offline biome **terrain** for games: a 16-bit heightmap (plus
per-layer weightmaps, tiling textures, and scatter rules in later milestones),
handed to `unreal-mcp-rx` to build a painted, foliaged, lit Landscape. The terrain
sibling of `pgap-3d-actor` / `pgap-sound`; shares their architecture, determinism,
and engine handoff.

Status: **scaffold (L0)** — spec + fail-closed validator + capability report +
a deterministic heightmap for `plain` (and a generic base for the other biomes).
Surfacing (weightmaps/textures), scatter, water, and biome-specific landforms are
L1–L5. Design: [PRD.md](PRD.md). Boundary with the engine: repo-root `SPLIT.md`.

v1 biomes: **plain, forest, snow (ice), ocean, shore, moon.**

## Usage

```bash
# from the repo root, via the wrapper:
python pgap.py landscape --capabilities          # the machine-readable contract
python pgap.py landscape --biome plain --out out
python pgap.py landscape --spec pgap-landscape/fixtures/plain.json --handoff --out out

# or directly (from this folder):
python -m psl.cli --biome snow --seed 3 --out out
```

Output (L0): `<Name>_Height.png` (16-bit) + `<Name>.landscape.import.json` +
`manifest.json`. `--handoff` also writes the `unreal-mcp-rx` source bundle
(currently the `Heightmap` role; the rest land in L1–L5).

## The split

pgap-landscape generates **what the land is and where each material/plant goes**
(engine-neutral data + a role-tagged manifest). `unreal-mcp-rx` imports the
heightmap, paints layers, scatters foliage, places water, and lights it. See
`SPLIT.md` at the repo root.

## Tests

```bash
cd pgap-landscape && python -m pytest -q     # determinism + fail-closed smoke
```
