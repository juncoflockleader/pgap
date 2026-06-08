# PRD: pgap-city — Procedural City Pipeline (psc)

Status: Draft v1 (planning).
Part of the `pgap` monorepo. Sibling of `pgap-3d-actor`, `pgap-sound`, and
`pgap-landscape`; shares their architecture, determinism guarantees, and
`unreal-mcp-rx` handoff.

---

## 1. Summary

Build a **deterministic, dependency-light, offline** generator that turns a city
spec (an **era × culture/style** pick plus size/seed) into **game-ready city
data** — a modular **building kit** (glTF meshes) plus a **city layout graph**
(streets → blocks → lots → building instances + props) plus a style palette —
exported as engine-neutral files + a manifest, rather than hand-modeled or
model-generated.

"Architecture B" for cities: don't ask a model to *build* the city — **assemble
buildings from a parametric module kit** and **lay them out by a deterministic
grammar**. pgap decides *what buildings exist and where every instance/prop goes*;
the `unreal-mcp-rx` bridge owns the engine "last mile" (import the kit, instance
the layout via HISM, lay roads, apply materials, light it, prove it in PIE — and
optionally drop the whole city onto a `pgap-landscape` tile).

v1 style cells (era × culture/style):
**futuristic × steampunk, futuristic × cyberpunk, modern × american, modern × japan.**

## 2. Problem & motivation

A scene needs a place. Hand-built cities are enormous effort and non-reproducible;
marketplace kits are fixed-style and license-bound; ML city generation is
non-deterministic and online. But a city is **two separable, synthesizable
problems**: (a) a *building* is a parametric stack of modules (footprint → floors →
roof → facade), and (b) a *city* is a layout grammar (street network → blocks →
lots → instances). Both are deterministic given a style profile and a seed. A
small pipeline turns one `(era, culture)` pick into a reproducible, instanceable
city that drops into the engine — and gives the landscapes and creatures the other
pipelines make a world to inhabit.

## 3. Goals / non-goals

### Goals
- Generate a **modular building kit** (parametric glTF meshes) + a **city layout
  graph** (JSON) + a style palette, from a structured city spec keyed by
  `(era, culture)`, exported engine-neutral with a `manifest.json`.
- **Deterministic:** same spec + seed → byte-identical kit + layout. No network in
  the core path.
- **Style-routed:** an `(era, culture)` tuple selects a **style profile** that
  drives every knob (roof form, wall material/palette, window/door rhythm,
  ornament, height distribution, street pattern, block shape, prop set, density).
- **Instancing-first:** the layout emits **instance transforms** (kit ref +
  transform + scale + variation seed) so the bridge can build HISM/ISM cheaply;
  landmarks are flagged for individual placement.
- **Composable & reuse-first:** building meshes use the `pgap-3d-actor`
  module-graph engine + surface synth; props/signage lean on `pgap-gear` later.
  pgap-city owns the **kit assembly grammar** and the **layout grammar**, not new
  mesh engines.
- **Fail-closed** capability report + validation, mirroring the siblings.
- Plug into `unreal-mcp-rx` via new manifest **roles** (BuildingKit, CityLayout,
  PropScatter, StyleMaterialSpec, RoadNetwork) — pgap makes no engine calls.

### Non-goals (v1)
- **Interiors / enterable buildings.** Exterior shells + facades only in v1.
- **The engine actions** — importing the kit, HISM instancing, road meshes,
  materials, lighting, navmesh. That is the bridge's "last mile." pgap emits data.
- **Full era × culture matrix.** v1 ships **four** cells (above); the registry is
  built to extend, but breadth is deferred.
- **Gameplay systems** (traffic AI, crowd sim, day/night logic). Static city in v1.
- **Photoreal / hero landmarks.** Stylized, owned, offline — the standard trade.
- **Terrain.** Comes from `pgap-landscape`; pgap-city consumes a tile's extent/sea
  level for placement but does not generate ground.

## 4. Users & use cases

- **An agent** turns "a rain-soaked cyberpunk downtown" into `{era: futuristic,
  culture: cyberpunk}` + size + seed, runs the CLI, and hands the bundle to
  `unreal-mcp-rx` to assemble a block.
- **A developer** wants a reproducible city backdrop for testing — same seed, same
  streets and skyline, every machine.
- **The composition lane:** `pgap-landscape` tile + pgap-city + `pgap-3d-actor`
  inhabitants + `pgap-sound` ambience, assembled by the bridge.

## 5. Key design insight: kit + grammar, not bespoke geometry

A believable city is **repetition with variation**. So split it:

1. **Building = module stack.** A footprint, N floor modules, a roof module, and
   facade detail (windows/doors/balconies/ornament) — assembled by the same
   module-graph engine `pgap-3d-actor` already uses. The **style profile** chooses
   which modules, materials, and rhythms. A handful of modules × parameters ×
   seeds yields endless buildings.
2. **City = layout grammar.** A street network (grid / organic / radial, chosen by
   `(era, culture)`) subdivides into blocks → lots; each lot gets a building
   *instance* (a kit ref + transform + per-instance variation seed) and props. The
   output is mostly **transforms**, not geometry — so the engine instances it
   cheaply (HISM), and the file stays small.

pgap owns *what exists and where* (kit + transforms, fully deterministic); the
bridge owns *how it's realized and proven*.

## 6. System architecture

```
city spec (JSON: {era, culture}, seed, size, density, layout, landmarks)
  → seeded PCG64 (one RNG, threaded)
  → style profile = resolve(era, culture)        # the knob table
  → street network: grid | organic | radial       # per style
  → blocks → lots (subdivide)                      # zoning: residential/market/civic
  → per kit-variant: building assembler            # footprint→floors→roof→facade (module graph)
  → instance placement: lot → (kitRef, transform, scale, varSeed)
  → props: lamps/signs/vehicles/vegetation density by zone+style
  → palette/materials spec
  → write: SK_/SM_<Kit>.gltf (kit meshes), <Name>.city.layout.json,
           StyleMaterialSpec.json, manifest.json  (+ --handoff source manifest)
```

### Modules
- **`styles`** — the `(era, culture)` → style-profile registry (the knob tables).
- **`network`** — street-network generators: grid (american), fine grid + alleys
  (japan), dense organic (cyberpunk), curved industrial (steampunk).
- **`blocks`** — block/lot subdivision + zoning.
- **`building`** — module-graph assembler: footprint, floor stack, roof, facade
  rhythm (windows/doors/balconies/ornament). Reuses 3d-actor's engine.
- **`facade` / `texture`** — window/sign patterns + tiling materials (surface synth:
  brick/concrete/glass/brass/panel).
- **`props`** — lamps, signage/billboards, vehicles, street vegetation by era+zone.
- **`layout`** — instance-transform emitter + landmark flags.
- **`spec` / `capabilities` / `nl`** — schema, fail-closed validator, machine
  report, prompt→spec inference.

### v1 style profiles (the four cells)
| `(era, culture)` | street net | silhouette / roof | materials & palette | signature props |
|---|---|---|---|---|
| **modern × american** | wide orthogonal grid, big blocks | low brick/glass storefronts + mid-rise towers, flat roofs | concrete / brick / glass, muted | traffic lights, sedans/trucks, lawns, street trees, parking |
| **modern × japan** | fine grid + narrow alleys, small lots | dense mixed-use mid-rise, flat/utilitarian roofs | white/grey panel + colorful **vertical signage** | vending machines, **power poles + wires**, kei cars, banners |
| **futuristic × cyberpunk** | dense, layered, organic-ish | tall **megablocks**, setbacks, antennas | dark bases + saturated **neon emissive**, holo-billboards, wet sheen | neon signs, drones, layered skyways, vapor |
| **futuristic × steampunk** | curved industrial, wide-medieval scaled up | **brass/iron** Victorian-industrial, domes, smokestacks | brass / copper / soot, warm; riveted plates, **pipes + gears** | gas lamps, airship mooring masts, steam vents, dirigibles |

## 7. Inputs & outputs

### Input: city spec (JSON)
```jsonc
{
  "name": "NeoDistrict",
  "era": "futuristic",                 // modern | futuristic  (v1; others fail closed)
  "culture": "cyberpunk",              // american|japan|cyberpunk|steampunk (v1)
  "seed": 5,
  "sizeBlocks": [4, 4],                // city extent in blocks
  "density": 0.8,                      // 0..1 lot fill + height bias
  "layout": "auto",                    // auto = style default (grid|fine_grid|organic|radial)
  "landmarks": ["tower"],              // optional flagged hero slots
  "terrain": { "tile": "AlpineValley", "seaLevel": 0.18 }  // optional pgap-landscape hook
}
```
`validate_spec` clamps ranges, drops unavailable props/landmarks (warnings), and
**errors** on an unsupported `(era, culture)` cell.

### Output (under `--out`)
- **`SM_<Kit>_*.gltf` / `SK_<Kit>_*.gltf`** — modular building kit meshes (+ their
  base-color/normal textures), per style variant.
- **`<Name>.city.layout.json`** — street network polylines, blocks, lots, and the
  **instance list** (`kitRef, transform, scale, varSeed, zone`), prop instances,
  landmark slots.
- **`StyleMaterialSpec.json`** — palette + per-kit material params.
- **`manifest.json`** — spec hash, seed, per-file SHA-1, license.
- With **`--handoff`**: the `unreal-mcp-rx` source manifest with roles
  `BuildingKit:<id>`, `CityLayout`, `PropScatter`, `StyleMaterialSpec`,
  `RoadNetwork`.

## 8. Functional requirements

- **FR1** Four `(era, culture)` style profiles (above), each producing a coherent
  kit + layout.
- **FR2** A modular building **kit** of instanceable glTF meshes per style, varied
  by parameter + seed.
- **FR3** A **street network** appropriate to the style (grid / fine-grid / organic
  / curved-industrial), subdivided into blocks → lots.
- **FR4** An **instance list** (kit ref + transform + scale + variation seed +
  zone) covering the lots; landmark slots flagged for individual placement.
- **FR5** **Prop scatter** (lamps, signage, vehicles, vegetation) by era + zone.
- **FR6** Style **palette + material spec** per kit.
- **FR7** Optional **terrain hook** — consume a `pgap-landscape` tile's extent/sea
  level so the city sits on real ground (z from terrain).
- **FR8** `--capabilities` JSON: eras, cultures, supported cells, module kinds,
  prop kinds, ranges.
- **FR9** Fail-closed validation; `--prompt`/`--describe` inference to a spec.
- **FR10** `--handoff` bundle with versioned roles, byte-stable.

## 9. Quality bar & acceptance

- **Determinism:** same (spec, seed) → byte-identical kit meshes + layout JSON
  (fixture-SHA test).
- **Validity:** kit meshes pass the 3d-actor mesh-validity bar (manifold, weighted
  if skinned, tri budget); layout instances reference real kit ids; no overlapping
  buildings on a lot; streets connected.
- **Style legibility:** a human (or the agent) can identify the `(era, culture)`
  from a render — cyberpunk reads neon-dense, steampunk reads brass-industrial,
  american reads grid+storefronts, japan reads dense+vertical-signage.
- **Engine round-trip:** the bridge imports the kit, HISM-instances the layout,
  lays roads, applies materials + lighting, and a PIE capture reads as the intended
  city (proof lane); optional compose onto a landscape tile.

## 10. Milestones (phased)

- **C0 — scaffold + spec + style registry + one kit.** Package, CLI,
  spec/validator, `styles` registry, building assembler producing the
  **modern × american** kit. Determinism test.
- **C1 — layout grammar + instances.** Grid network → blocks → lots → instance
  list + `city.layout.json` + material spec. Bridge proves import + HISM
  instancing on american.
- **C2 — modern × japan.** Fine grid + alleys, vertical signage, power-pole props.
- **C3 — futuristic × cyberpunk.** Megablock kit, neon/holo signage, emissive
  palette, organic-dense layout.
- **C4 — futuristic × steampunk.** Brass/iron kit, pipes/gears ornament, smokestacks
  + airship masts, curved-industrial layout.
- **C5 — composition.** Terrain hook: drop a city onto a `pgap-landscape` tile;
  full `--handoff` for all four cells.

## 11. Determinism, provenance, licensing

One seeded `PCG64` threaded through every stage; pure-function stages; I/O at the
edges only. No wall-clock, UUIDs, or set/dict-ordering nondeterminism. Per-instance
variation comes from a derived sub-seed, never re-seeded RNG. Every generation path
ships a fixture-SHA check. Output is original procedural work; manifest records
spec hash, seed, per-file SHA-1, and a license note.

## 12. Risks & mitigations

- **Instance count explosion** (a city is huge) → emit transforms, not geometry;
  the bridge builds HISM/ISM; cap kit variants and rely on per-instance variation.
- **Repetition reads as "copy-paste"** → per-instance variation seed (height,
  trim, color jitter, rotation) + a few kit variants per style.
- **Style not legible** → lean on signature props + palette + roof silhouette; test
  with renders per cell.
- **Layout overlaps / disconnected streets** → validate lot occupancy + network
  connectivity before write.
- **Scope creep into interiors/gameplay** → exterior-only, static, v1 non-goals.
- **Kit ↔ engine pivot/scale mismatch** → reuse the 3d-actor import sidecar
  conventions (units, up-axis); test round-trip early in C1.

## 13. Dependencies & constraints

- Pure Python + numpy; glTF + PNG written directly.
- Reuses `pgap-3d-actor` module-graph engine + surface synth for kit meshes/textures
  — do not reimplement geometry here. Props/signage may later lean on `pgap-gear`.
- Bridge gaps to confirm/build: **bulk HISM/ISM placement from a transform list**,
  **road spline/mesh** placement, style **material/lighting** application,
  optional **compose-onto-landscape**. (Static-mesh import + actor placement +
  lighting presets already exist in the bridge.)

## 14. Open questions

- Instance delivery: a flat **instance list** vs a **PCG-friendly point set** — likely
  list primary; revisit if PCG instancing is preferred by the bridge.
- "Culture" axis naming: cyberpunk/steampunk are *styles/aesthetics* more than
  cultures — keep one `(era, culture)` registry, or split `era × culture × style`?
  v1 treats them as cells of one registry; revisit if it gets crowded.
- Road representation: spline + road mesh vs decal vs landscape-layer — decide with
  the bridge in C1.
- Block/lot grammar: how organic before it stops reading as a planned city.
- LODs / nanite: bake LODs in pgap or rely on engine? Defer to post-v1.

## 15. Relationship to siblings & unreal-mcp-rx

- **pgap-3d-actor** provides the kit-assembly engine + surface synth, and populates
  the city with inhabitants/vehicles.
- **pgap-landscape** provides the ground the city sits on (shared extent/sea-level
  contract for the optional terrain hook).
- **pgap-sound** provides ambience (traffic hum, neon buzz, steam hiss) per style.
- **unreal-mcp-rx** owns every engine action: import the kit, HISM-instance the
  layout, lay roads, apply per-style materials + lighting, optionally compose onto
  a landscape tile, and prove it in PIE. pgap ships files + a role-tagged manifest;
  the bridge needs no knowledge of layout grammar.
