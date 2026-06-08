# PRD: pgap-landscape — Procedural Landscape Pipeline (psl)

Status: Draft v1 (planning).
Part of the `pgap` monorepo. Sibling of `pgap-3d-actor` and `pgap-sound`; shares
its architecture, determinism guarantees, and `unreal-mcp-rx` handoff.

---

## 1. Summary

Build a **deterministic, dependency-light, offline** generator that turns a biome
spec (e.g. `"a snowy mountain valley"`, `"a forest of rolling hills"`, `"a moon
crater field"`) into **game-ready terrain data** — a 16-bit heightmap, per-layer
material weightmaps, tiling surface textures, and deterministic scatter rules —
exported as engine-neutral files + a manifest, rather than sculpted by hand or
produced by a model.

This is "Architecture B" for terrain, the direct analog of `pgap-3d-actor`: don't
ask a model to *paint* the terrain — **construct the heightfield algorithmically**
(noise + erosion + stamps) and derive surfacing by **rule** (slope/altitude/
curvature). pgap decides *what the land is and where each material/plant goes*;
the `unreal-mcp-rx` bridge owns the engine "last mile" (import the heightmap into a
Landscape, paint layers, scatter foliage, water, sky/lighting, runtime proof).

v1 biomes: **plain, forest, snow (ice), ocean, shore, moon.**

## 2. Problem & motivation

Every scene needs ground. Hand-sculpting terrain is slow and non-reproducible;
marketplace heightmaps are fixed and license-bound; ML terrain is non-deterministic
and online. Yet terrain is **eminently synthesizable** — fBm/ridged/Worley noise,
cheap erosion, and crater stamps cover a huge range of believable landforms, and
the *surfacing* (where snow vs rock vs grass sits) is a deterministic function of
slope and altitude. A small parametric pipeline turns one prompt/spec into a
reproducible biome that drops straight into the engine — and gives the creatures
`pgap-3d-actor` makes somewhere to stand.

## 3. Goals / non-goals

### Goals
- Generate **game-ready terrain data** from a structured biome spec: a 16-bit
  heightmap, normalized per-layer weightmaps, tiling base-color/normal textures,
  and a scatter-rule sidecar — all engine-neutral, plus a `manifest.json`.
- **Deterministic:** same spec + seed → byte-identical files. No network in the
  core path.
- **Biome-routed:** a curated set of biome recipes (plain / forest / snow / ocean
  / shore / moon), each a parameterized noise+erosion+surfacing stack.
- **Rule-based surfacing:** layer masks and foliage/prop density derived from
  slope, altitude, and curvature — not hand-painted — so they always match the
  heightfield.
- **Composable & reuse-first:** trees, rocks, and props come from `pgap-3d-actor`;
  surface textures from its surface synth. This pipeline owns the *field* and the
  *rules*, not new mesh/texture engines.
- **Fail-closed** capability report + validation, mirroring the other pipelines.
- Plug into `unreal-mcp-rx` via new manifest **roles** (Heightmap, Weightmap,
  LandscapeMaterialSpec, FoliageRule, WaterPlane, SkyProfile) — pgap makes no
  engine calls.

### Non-goals (v1)
- **In-engine sculpting / live editing.** Bake files offline; the bridge imports.
- **The Landscape actor, layer painting, foliage instancing, water, lighting.**
  That is the bridge's job (the "last mile"). pgap emits data + rules only.
- **World-Partition / streaming-proxy / runtime-virtual-texture authoring.** A
  later concern; v1 targets a single landscape tile.
- **Photoreal terrain / megascan-grade detail.** Stylized, owned, offline — the
  same deliberate trade as the 3D and audio siblings.
- **Hydrology simulation at scale.** Erosion is a cheap stylized pass, not a
  physically-accurate solver.
- **Mesh terrain (voxel/marching-cubes caves, overhangs).** Heightfield only in
  v1; overhangs/arches are out (heightfields can't represent them).

## 4. Users & use cases

- **An agent** turns "snowy alpine valley with a frozen lake" into a biome spec,
  runs the CLI, and hands the bundle to `unreal-mcp-rx` to build a playable tile.
- **A developer** wants a reproducible test environment for the creatures/cities
  the other pipelines make — same seed, same world, every machine.
- **The composition lane**: landscape + `pgap-city` + `pgap-3d-actor` + `pgap-sound`
  assembled by the bridge into one scene.

## 5. Key design insight: heightfield-first, surfacing-by-rule

Terrain is a **2-D scalar field** (height) plus a small set of **masks** (which
material, where). The field is cheap to synthesize deterministically; the masks
are a *pure function* of the field's derivatives (slope, altitude, curvature), not
artist decisions. So:

1. Build height as a seeded noise stack tuned per biome, then a cheap erosion pass
   for believability (talus/thermal; optional hydraulic-lite streaks).
2. Derive every layer weightmap and every scatter density from height + slope +
   curvature thresholds the biome recipe declares. Snow accumulates on low slope &
   high altitude; rock shows on steep slope; grass on gentle low ground; sand near
   sea level; regolith everywhere on the moon.

This keeps the output **consistent** (surfacing can never disagree with the
terrain) and **tiny** (recipes are code + small tables), and leaves placement of
the heightmap, layers, and plants to the engine — which is what it's good at.

## 6. System architecture

```
biome spec (JSON)
  → seeded PCG64 (one RNG, threaded)
  → height field:  base noise (fBm + ridged + Worley) → biome warp → stamps (craters) → erosion pass
  → derivatives:   slope, altitude-normalized, curvature
  → surfacing:     per-layer weightmap deriver (rule thresholds) → normalize
  → textures:      tiling base-color + normal per layer (reuse 3d-actor surface synth)
  → scatter rules: species/prop density fields by layer×slope×altitude (+ seed)
  → water/sky:     sea level + sky/lighting/post profile hint
  → write:         Heightmap.png (16-bit), Weightmap_<layer>.png, T_<layer>_*.png,
                   landscape.import.json, manifest.json  (+ --handoff source manifest)
```

### Modules
- **`field`** — noise primitives (fBm, ridged multifractal, Worley/cellular),
  domain warp, biome-specific combinators.
- **`erosion`** — cheap thermal (talus) + optional hydraulic-lite; stylized, bounded
  iteration count for determinism/speed.
- **`stamps`** — crater field (moon), plateau/valley carving.
- **`surfacing`** — slope/altitude/curvature derivation + rule evaluator →
  normalized weightmaps.
- **`texture`** — tiling layer textures + normal maps (shared surface synth).
- **`scatter`** — deterministic density fields and/or point lists per species/prop,
  referencing `pgap-3d-actor` assets by role.
- **`biomes`** — the curated recipe registry (plain/forest/snow/ocean/shore/moon).
- **`spec` / `capabilities` / `nl`** — schema, fail-closed validator, machine
  report, and prompt→spec inference (mirrors 3d-actor).

## 7. Inputs & outputs

### Input: landscape spec (JSON)
```jsonc
{
  "name": "AlpineValley",
  "biome": "snow",                     // plain|forest|snow|ocean|shore|moon (others fail closed)
  "seed": 12345,
  "sizeKm": 2.0,                       // world extent of the tile
  "resolution": 1009,                  // N*N+1 (UE-friendly: 505/1009/2017)
  "heightScaleM": 600,                 // meters from min to max
  "seaLevel": 0.18,                    // 0..1 in normalized height (water at/below)
  "ruggedness": 0.7,                   // 0..1 biome-clamped noise/erosion intensity
  "layers": ["snow", "rock", "scree"], // material layers (biome provides defaults)
  "scatter": { "density": 0.4, "species": ["pine", "boulder"] },  // refs 3d-actor roles
  "palette": "cool blue-white"         // free text; biome provides default
}
```
`validate_spec` clamps out-of-range values, drops unavailable layers/species
(warnings), and **errors** on an unsupported biome.

### Output (under `--out`)
- **`<Name>_Height.png`** — 16-bit grayscale heightmap, `resolution`².
- **`<Name>_Weight_<layer>.png`** — one normalized 8/16-bit mask per layer.
- **`T_<layer>_BaseColor.png` / `T_<layer>_Normal.png`** — tiling layer textures.
- **`<Name>.landscape.import.json`** — sidecar: sizeKm, resolution, heightScaleM,
  seaLevel, layer order + blend rules, scatter rules, sky/lighting/post profile,
  palette.
- **`manifest.json`** — spec hash, seed, per-file SHA-1, license note.
- With **`--handoff`**: the `unreal-mcp-rx` source manifest with roles
  `Heightmap`, `Weightmap:<layer>`, `LandscapeMaterialSpec`, `FoliageRule`,
  `WaterPlane`, `SkyProfile`.

## 8. Functional requirements

- **FR1** Six biome recipes: plain, forest, snow, ocean, shore, moon.
- **FR2** 16-bit heightmap at a UE-friendly resolution; valid full-range usage.
- **FR3** Per-layer weightmaps that **sum to ≤1 per texel** and match the terrain by
  rule (no manual painting).
- **FR4** Tiling, seamless layer textures + normal maps per layer.
- **FR5** Deterministic scatter rules referencing `pgap-3d-actor` assets by role
  (trees, boulders, props); ocean/moon scatter ≈ none by default.
- **FR6** `seaLevel` + water flag for ocean/shore; sky/lighting/post profile hint
  per biome (cool-fog for snow, black-sky/harsh-sun for moon, etc.).
- **FR7** `--capabilities` JSON: biomes, layer vocabulary, species roles, ranges.
- **FR8** Fail-closed validation; `--prompt`/`--describe` inference to a spec.
- **FR9** `--handoff` bundle with versioned roles, byte-stable.

## 9. Quality bar & acceptance

- **Determinism:** same (spec, seed) → byte-identical heightmap, masks, textures
  (fixture-SHA test).
- **Validity:** heightmap is single-channel 16-bit at declared resolution; masks
  normalized; textures power-of-two and tile seamlessly (edge-wrap test).
- **Coherence:** snow only on low-slope/high-altitude; rock on steep slope; sand
  near sea level; craters only on moon — asserted by sampling masks against
  slope/altitude.
- **Engine round-trip:** the bridge imports the heightmap into a Landscape, paints
  the layers, scatters foliage, and a PIE capture shows the biome reading as
  intended (proof lane).

## 10. Milestones (phased)

- **L0 — scaffold + spec + plain heightmap.** Package, CLI, spec/validator,
  `field`+`erosion`, write a 16-bit heightmap for **plain**. Determinism test.
- **L1 — surfacing + material spec.** Slope/altitude rule evaluator → normalized
  weightmaps + tiling textures + `landscape.import.json`. Bridge proves
  heightmap-import + layer-paint on plain.
- **L2 — scatter + reuse.** Scatter-rule emitter referencing 3d-actor trees/rocks;
  bridge foliage proof. **forest** biome lands here.
- **L3 — moon.** Crater stamps + regolith; black-sky profile; no foliage.
- **L4 — ocean + shore.** Sub-sea-level fields + `WaterPlane` role + beach/foam
  surfacing (needs the bridge water tool).
- **L5 — snow + sky profiles.** Ridged alpine + glacial valleys; cool-fog
  `SkyProfile`. Full `--handoff` for all six biomes.

## 11. Determinism, provenance, licensing

One seeded `PCG64` threaded through every stage; pure-function stages; I/O at the
edges only. No wall-clock, UUIDs, or set/dict-ordering nondeterminism. Every
generation path ships a fixture-SHA check. Output is original procedural work;
manifest records spec hash, seed, per-file SHA-1, and a license note.

## 12. Risks & mitigations

- **Erosion cost/instability** → bounded iteration count, stylized (not physical),
  tested for determinism.
- **Seam/tiling artifacts** in layer textures → equal-edge / wrap tests; reuse the
  proven surface synth.
- **Heightmap resolution / scale mismatch** with UE Landscape component sizing →
  emit only UE-recommended `N*N+1` sizes; sidecar declares meters explicitly.
- **Weightmap > 1 blowout** → normalize as the final surfacing step; test.
- **Scatter divergence from terrain** → derive density from the *same* field
  derivatives the masks use; never random-place.

## 13. Dependencies & constraints

- Pure Python + numpy; PNG written directly (16-bit grayscale support required).
- Reuses `pgap-3d-actor` for trees/rocks/props and the surface-texture synth — do
  not reimplement geometry/texture engines here.
- Bridge gaps to confirm/build: file **heightmap import** into a Landscape,
  **weightmap layer paint** from files, **water body** creation, biome
  **sky/lighting/post** presets. (Foliage scatter + layer/heightmap reflection
  already exist in the bridge.)

## 14. Open questions

- Heightmap exchange format: 16-bit PNG vs RAW/r16 — confirm the bridge importer's
  preferred path in L1.
- Scatter contract: emit **rules** (let the bridge/PCG place against the real
  landscape) vs a **baked point list** — likely rules primary, baked list as
  fallback. Decide in L2.
- Multi-tile / World-Partition: single tile in v1; revisit for large worlds.
- How much erosion is "enough" stylistically before cost outweighs benefit.

## 15. Relationship to siblings & unreal-mcp-rx

- **pgap-3d-actor** supplies the meshes scattered on the terrain (trees, rocks,
  props) and the surface-texture synth — landscape is the *ground* those actors
  stand on.
- **pgap-city** drops onto a landscape tile (composition); shared `seaLevel`/extent
  contract so a city sits correctly on terrain.
- **unreal-mcp-rx** owns every engine action: create the Landscape, import the
  heightmap, create LayerInfos + paint weightmaps, build the layer-blend material,
  scatter foliage, place water, set sky/lighting/post, and prove it in PIE. pgap
  ships files + a role-tagged manifest; the bridge needs no knowledge of noise.
