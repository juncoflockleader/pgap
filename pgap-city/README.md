# pgap-city (psc) — Procedural City Pipeline

Deterministic, offline **cities**: a modular building kit + a city layout graph
(streets → blocks → lots → instance transforms + props), handed to `unreal-mcp-rx`
to import and bulk-instance (HISM). Sibling of `pgap-3d-actor` / `pgap-sound` /
`pgap-landscape`; shares their architecture, determinism, and engine handoff.

Status: **scaffold (C0)** — style registry for the four v1 cells + spec +
fail-closed validator + capability report + a deterministic grid **layout**
(instance transforms). Building-kit glTF assembly (reusing the pgap-3d-actor
module engine), roads, and prop meshes are C1+. Design: [PRD.md](PRD.md). Boundary
with the engine: repo-root `SPLIT.md`.

v1 cells (era × culture/style):
**futuristic×steampunk, futuristic×cyberpunk, modern×american, modern×japan.**

## Usage

```bash
# from the repo root, via the wrapper:
python pgap.py city --capabilities
python pgap.py city --era modern --culture american --out out
python pgap.py city --spec pgap-city/fixtures/american.json --handoff --out out
```

Output (C0): `<Name>.city.layout.json` (streets/blocks/lots/instances/props) +
`StyleMaterialSpec.json` + `manifest.json`. `--handoff` also writes the
`unreal-mcp-rx` source bundle (`CityLayout` + `StyleMaterialSpec` roles; the
`BuildingKit` / `RoadNetwork` / `PropScatter` roles land in C1+).

## The split

pgap-city generates **what buildings exist and where every instance/prop goes**
(engine-neutral kit + layout + a role-tagged manifest). `unreal-mcp-rx` imports the
kit, HISM-instances the layout, lays roads, applies per-style materials/lighting,
and optionally composes the city onto a `pgap-landscape` tile. See `SPLIT.md`.

## Tests

```bash
cd pgap-city && python -m pytest -q     # determinism + fail-closed + all-cells smoke
```
