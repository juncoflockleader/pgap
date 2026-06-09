# pgap-city (psc) — Procedural City Pipeline

Deterministic, offline **cities**: a modular building kit + a city layout graph
(streets → blocks → lots → instance transforms + props), handed to `unreal-mcp-rx`
to import and bulk-instance (HISM). Sibling of `pgap-3d-actor` / `pgap-sound` /
`pgap-landscape`; shares their architecture, determinism, and engine handoff.

Status: **C1 — skinned building kits.** Style registry for the four v1 cells + spec
+ fail-closed validator + capability report + a deterministic grid **layout**
(instance transforms), and each building kit is now **skinned**: a synthesized
facade texture (wall + window grid + ground floor + parapet, base-color + normal,
optional emissive lit windows) on the walls and a roof texture on top, embedded in
`SM_<kit>.gltf` — so the HISM skyline reads as real buildings, per cell. Roads and
prop meshes are C2+. Design: [PRD.md](PRD.md). Boundary: repo-root `SPLIT.md`.

v1 cells (era × culture/style):
**futuristic×steampunk, futuristic×cyberpunk, modern×american, modern×japan.**

## Usage

```bash
# from the repo root, via the wrapper:
python pgap.py city --capabilities
python pgap.py city --era modern --culture american --out out
python pgap.py city --spec pgap-city/fixtures/american.json --handoff --out out
```

Output: `<Name>.city.layout.json` (streets/blocks/lots/instances/props) +
`StyleMaterialSpec.json` + per-kit `SM_<kit>.gltf` (skinned, textures embedded) +
`SM_<kit>_BaseColor/Normal/Roof[/Emissive].png` (inspection) + `<Name>.instances.json`
(HISM) + `<Name>_Plan.png` + `manifest.json`. `--handoff` also writes the
`unreal-mcp-rx` source bundle (`CityLayout` + `StyleMaterialSpec` + `BuildingKit:*`
roles; `RoadNetwork` / `PropScatter` land in C2+).

Per-instance window scale uses the kit's representative size; pixel-uniform windows
across every instance size want a UE world-aligned/triplanar facade material (a
documented handoff upgrade).

## The split

pgap-city generates **what buildings exist and where every instance/prop goes**
(engine-neutral kit + layout + a role-tagged manifest). `unreal-mcp-rx` imports the
kit, HISM-instances the layout, lays roads, applies per-style materials/lighting,
and optionally composes the city onto a `pgap-landscape` tile. See `SPLIT.md`.

## Tests

```bash
cd pgap-city && python -m pytest -q     # determinism + fail-closed + all-cells smoke
```
