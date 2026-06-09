# SPLIT — pgap ⇄ unreal-mcp-rx responsibilities

One rule, applied to every pipeline:

> **pgap decides _what exists and where_** (offline, deterministic, engine-neutral
> data + assets + a role-tagged manifest). **unreal-mcp-rx decides _how it is
> realized in the engine and proves it_** (import, author, place, light, runtime
> proof).
>
> pgap never calls the engine. The bridge never does noise math, layout grammar,
> or geometry synthesis. The **manifest role** is the only seam between them.

The bridge-side counterpart to this doc lives in `unreal-mcp-rx` at
`docs/features/landscape-and-city-last-mile-plan.md`.

## Responsibility matrix

| Pipeline | pgap produces (engine-neutral) | unreal-mcp-rx does (the last mile) |
|---|---|---|
| **3d-actor** | rigged glTF + textures + import sidecar + manifest | import → SkeletalMesh/Skeleton/Anims/Material; assemble Blueprint; place; PIE proof |
| **sound** | WAV + `SoundWave` sidecar + manifest | import as `SoundWave`; wire onto actor/Blueprint; proof |
| **landscape** | 16-bit heightmap, per-layer weightmaps, tiling layer textures, scatter rules, `landscape.import.json` | create ULandscape; import heightmap; LayerInfo + paint weightmaps; layer-blend material; foliage scatter; water; sky/lighting/post; PIE proof |
| **city** | modular building kit (glTF), `city.layout.json` (streets→blocks→lots→instances + props), style material spec | import kit; bulk HISM/ISM-instance the layout; landmarks as actors; roads; per-style materials/lighting; optional compose-onto-landscape; PIE proof |
| **gear** | weapon/shield static meshes + import sidecar | import; attach/equip at grip socket; materials; proof |

Determinism, dependency-light (pure Python + numpy), stylized-not-photoreal, and
fail-closed validation are pgap invariants for **all** rows (see `CLAUDE.md`).

## The seam: manifest roles

pgap emits files tagged with a **role** in the handoff manifest (the
`game.…agent_source_manifest` family). The bridge maps **role → apply tool**,
validates fail-closed against its capability report, and runs its standard guarded
(dry-run → confirm → rollback → proof) apply. Adding a feature = adding roles, not a
new protocol.

| Feature | Roles pgap emits |
|---|---|
| 3d-actor | `SkeletalMesh`/`StaticMesh`, `Animation`, `Texture`, `Material`, `Skeleton` |
| sound | `Sound` |
| **landscape** | `Heightmap`, `Weightmap:<layer>`, `LandscapeMaterialSpec`, `FoliageRule`, `WaterPlane`, `SkyProfile` |
| **city** | `BuildingKit:<id>`, `CityLayout`, `PropScatter`, `StyleMaterialSpec`, `RoadNetwork` |

Every role/sidecar is versioned (`schemaVersion`); pgap and the bridge stay in
lockstep on that version.

## Who owns a decision? (quick test)

- Involves **noise, erosion, layout grammar, module assembly, or "where does X
  go"** → **pgap**.
- Involves a **UObject, asset import, material/Blueprint authoring, placement,
  lighting, water, navmesh, or PIE** → **unreal-mcp-rx**.
- Involves **reusing meshes/textures across pipelines** (trees on terrain, props in
  a city) → pgap composes from `pgap-3d-actor`; the bridge only ever sees finished
  files + roles.

## Per-pipeline detail

- `pgap-landscape/PRD.md`, `pgap-city/PRD.md` — pgap scope + milestones (L0–L5,
  C0–C5).
- `unreal-mcp-rx` `docs/features/landscape-and-city-last-mile-plan.md` — the
  bridge gaps (heightmap import, weightmap paint, water body, bulk instancing,
  roads, biome sky presets) + milestones (B-L1–B-C3).
