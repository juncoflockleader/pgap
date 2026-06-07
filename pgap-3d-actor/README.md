# pgap — Procedural Generative Asset Pipeline

Deterministic, dependency-light procedural generation of **game-ready 3D actors** —
geometry, skeleton, skin weights, animations, and textures — exported as glTF for
Unreal Engine (or any glTF engine).

This is "Architecture B" from the `unreal-mcp-rx` 3D-generation analysis: rather
than calling an external text-to-3D service, pgap **owns the whole stack** so
output is offline, reproducible, free, and consistent in style (stylized, not
photoreal). It is **pure Python + numpy** (~160 KB of source, no ML framework, no
graphics engine) — because the 3D is *constructed by algorithms*, not approximated
by a trained model. An LLM only ever fills in the *parameters*.

## Quickstart

```bash
# generate a rigged, skinned, animated, textured glTF from a spec
python -m pgap.cli --spec fixtures/dog_golden_retriever.json --out out

# or from a natural-language prompt (v1 archetypes)
python -m pgap.cli --prompt "a small golden retriever that wags its tail and barks" --out out

# v2 modular creatures — a preset chimera (strict) or a described one (free)
python -m pgap.cli --creature beholder --color purple --out out
python -m pgap.cli --describe "a deer-antlered dragon with feathered wings and tusks" --mode free --out out

# discover what's supported (machine-readable; what an LLM reads)
python -m pgap.cli --capabilities        # v1: archetypes, traits, animations, coats
python -m pgap.cli --v2-capabilities     # v2/v3: modules, variants, sockets, templates
```

Each run writes a self-contained `<Name>.gltf` (mesh + skin + animations + PBR
material + embedded texture), a `<Name>_BaseColor.png`, an `<Name>.import.json`
sidecar, and a `manifest.json`. Drop the `.gltf` into any glTF viewer to inspect,
or import it into Unreal.

## What it can generate

- **v1 — archetypes:** `prop` (rigless static rocks/barrels), `quadruped` (the
  golden-retriever reference case — breed-accurate ears/snout/tail), and `biped`
  (a stylized humanoid). Parametric coats, traits, proportions, and animations.
- **v2 — modular chimeras:** creatures composed from socketed body-part modules —
  beholder, kraken, octopus-dragon, sphinx, merfolk, cthulhu, dragon, … — any
  body plan (bilateral, radial, tentacled, winged) from one ~22-module library.
- **v3 — part variants:** each part has named forms — wings (bat/feathered/
  membrane/insect), horns (unicorn/antler/ram/bull/rhino), heads, ears, tusks,
  hooves, claws, manes — so *"a winged lion"* and *"a unicorn"* diverge correctly.

All of it flows through **one unchanged pipeline**, and every output imports into
Unreal as a SkeletalMesh/StaticMesh + Skeleton + AnimSequences + Texture +
Material (verified live in UE 5.7).

## How it works

**Skeleton-first.** Build the canonical rig first, synthesize geometry *around* the
bones (tapered-capsule SDF + smooth-min → marching cubes), and derive skin weights
from distance-to-bone. Rigging and skinning are then correct **by construction**,
and animations are joint-rotation tracks that retarget trivially.

**Everything composes through one SDF mesh.** The geometry kernel smooth-mins a
*list of blobs* — it doesn't know whether they form a dog or a cthulhu. Skinning,
UV, texture, and animation are equally body-agnostic. That is why v2 (modular
creatures) and v3 (part variants) are mostly *new data*, not new machinery.

```
prompt / spec / recipe ─▶ validate (fail-closed) ─▶ [one seeded PCG64 RNG]
   ▶ skeleton ▶ parts ▶ geometry (SDF→marching cubes) ▶ skin ▶ uv ▶ paint
   ▶ texture ▶ animate ▶ assemble glTF (+ import.json + manifest)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full pipeline, the
working model with `unreal-mcp-rx`, and why it needs no LLM backend.

## Two authoring interfaces

- **v1 spec** (JSON) — archetype + proportions + traits + material + animations.
  Schema in [PRD.md §7](PRD.md). The NL front-end (`--prompt`) infers it.
- **v2/v3 recipe** (JSON) — a creature as a graph of socketed module instances,
  each with an optional `variant`. The NL front-end (`--describe`) infers it,
  `--strict` picks a preset template, `--free` composes from features.

Both are guarded by a **fail-closed validator**: unsupported archetypes, unknown
modules/variants, missing sockets, etc. are rejected, not guessed.

## Determinism & testing

One `numpy.random.Generator(PCG64(seed))` is threaded through every stage and
never re-seeded; stages are pure functions; I/O only at the edges. **Same (spec,
seed) → byte-identical output** on any machine. The suite (131 tests) asserts mesh
validity, skin-weight correctness, SHA stability, and a variant/creature corpus.

```bash
python -m pytest tests/        # or run the test fns directly if pytest isn't installed
```

## Relationship to unreal-mcp-rx

pgap is the **content generator**; `unreal-mcp-rx` is the **engine bridge** (a live
MCP server that imports, authors materials, assembles Blueprints, and runs
PIE proofs). The seam is the M5 **source-handoff bundle** (`SK_/A_/T_` files + a
`game.interactive_component_agent_source_manifest.v1` manifest, via `--handoff`).
pgap output is plain glTF, so the bridge is swappable per engine.

## Docs

| Doc | What |
|---|---|
| [PRD.md](PRD.md) | Product requirements, spec schema, milestones M0–M7 |
| [DESIGN.md](DESIGN.md) | Per-stage algorithms & data structures |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Pipeline, working model, why no LLM / lightweight |
| [AGENTS.md](AGENTS.md) | **How an AI agent drives pgap** (capabilities, schemas, recipes) |
| [docs/milestones/](docs/milestones/) | M0–M7 implementation plans + exit criteria |
| [docs/design/v2-modular-creatures.md](docs/design/v2-modular-creatures.md) | Composable chimeras |
| [docs/design/v3-part-variants.md](docs/design/v3-part-variants.md) | Part variants & library |
| [docs/roadmap/](docs/roadmap/) | Where it grows next: surfaces → library/bestiary → v4 faces |

## Status

v1 (M0–M7), v2 (modular creatures), and v3 (part variants) are **implemented and
live-verified in UE 5.7**. Stylized by design; the optional image-gen texture path
remains the only place a model could plug in (cached, with a procedural fallback).
