# CLAUDE.md — pgap-3d-actor

Guidance for the 3D-actor pipeline. Inherits the monorepo-wide principles in the
top-level [../CLAUDE.md](../CLAUDE.md); this file adds the 3D specifics. The
authoritative spec is **[PRD.md](PRD.md)**; the design is **[DESIGN.md](DESIGN.md)**;
forward direction is in `docs/roadmap/`.

## Core design (do not violate without discussion)

- **Skeleton-first.** Build the canonical rig first, synthesize geometry around the
  bones (tapered-capsule SDF + smooth-min → marching cubes), derive skin weights
  from distance-to-bone. Never bolt on a post-hoc auto-rigger. This is why rigging
  and skinning are correct by construction, and why everything composes.
- **Everything composes through one SDF mesh.** The geometry kernel smooth-mins a
  *list of blobs* — it doesn't know whether they form a dog or a cthulhu. Skinning,
  UV, texture, and animation are body-agnostic. So new creatures/parts/variants are
  mostly *data*, not new machinery. Keep it that way (no second geometry path).
- **Two generations, one pipeline:**
  - **v1** (`pgap/`) — archetype-routed: prop / quadruped / biped; spec-driven.
  - **v2/v3** (`pgap/v2/`) — modular creatures from socketed part modules with
    named **variants**; recipe-driven. Both run the same geometry→skin→uv→texture→
    animate stages.
- **Bone-name contract.** Generated bone names must match the animation library and
  the `import.json` sidecar so behaviors bind without retargeting.

## Outputs & the unreal-mcp-rx contract

Produce `<Name>.gltf` (skeletal/static mesh + skin + animations + PBR material +
embedded texture), `<Name>_BaseColor.png`, `<Name>.import.json` (target skeleton,
tail bone, bone list, clips), and `manifest.json`. With `--handoff`, emit the
role-named source bundle (`SK_/A_/T_` + `game.interactive_component_agent_source_
manifest.v1`) the project-clone proof lane consumes.

## Quality bar (reference acceptance)

Regenerate the golden retriever and pass the `unreal-mcp-rx` project-clone proof
lane (bark + tail-wag PIE) — a *recognizable dog*, not a placeholder. The library
then generalizes to chimeras (v2) and part variants (v3); the variant corpus
(`tests/test_v3_corpus.py`) is the regression gate for any new part.

## Run

```bash
python -m pgap.cli --creature dragon --out out      # from this folder
# or, from the repo root via the wrapper:
python ../pgap.py 3d-actor --creature dragon --out out
```
