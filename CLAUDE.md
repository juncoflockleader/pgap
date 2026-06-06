# CLAUDE.md — pgap

Guidance for Claude working in this repository.

## What this is

`pgap` (Procedural Generative Asset Pipeline) generates game-ready 3D actors
procedurally — geometry, skeleton, skin weights, animations, textures — for
Unreal Engine, without an external text-to-3D service. It is "Architecture B"
from the `unreal-mcp-rx` analysis. The authoritative spec is **[PRD.md](PRD.md)**;
read it before designing or implementing anything.

## Core design (do not violate without discussion)

- **Skeleton-first.** Build the canonical rig first, synthesize geometry around
  the bones (SDF/metaballs → marching cubes), derive skin weights from
  distance-to-bone. Never bolt on a post-hoc auto-rigger.
- **Deterministic.** Same (spec, seed) → byte-identical output. One seeded RNG
  threaded through every stage. No wall-clock, no UUIDs, no set/dict-ordering
  nondeterminism. The core path makes no network calls.
- **Dependency-light.** Pure Python + numpy for the core. glTF written directly.
  The only optional online input is base-color texture image-gen, which is
  isolated, cached, and has a procedural fallback.
- **Stylized, not photoreal.** That is the deliberate trade for owning the stack.
  Hero/photoreal assets are a separate path (external services), out of scope.
- **Archetype-routed.** prop (no rig) / quadruped / biped. Ship the quadruped
  "dog" reference case end-to-end before generalizing (PRD milestones M0–M7).

## Outputs & the contract with unreal-mcp-rx

- Produce: `<Name>.gltf` (skeletal mesh + skin + animations), texture PNGs,
  `<Name>.import.json` (target skeleton, tail bone, skeleton policy), and a
  `manifest.json` (spec hash, seed, generator version, per-file SHA, license note).
- The `unreal-mcp-rx` MCP server consumes these for import / material authoring /
  Blueprint assembly / behavior / runtime proof. That "last mile" is built and
  reused unchanged — do not reimplement it here.
- Bone names in the generated skeleton MUST match the animation library and the
  `import.json` sidecar so behaviors bind without retargeting.

## Conventions

- This is a planning-stage repo: PRD + repo hygiene files only, **no scaffolding
  yet**. Do not create empty `src/`/`docs/` trees or boilerplate unless asked.
- Determinism is testable: a fixture spec re-run must diff to an identical output
  SHA; add such a check before/with any generation code.
- Commit messages: imperative subject; end with
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Default branch is `main`. Only commit/push when the user asks.

## Quality bar (reference acceptance)

Regenerate the golden retriever from a spec and have it import + assemble + pass
the existing `unreal-mcp-rx` project-clone proof lane (bark + tail-wag PIE) — with
a *recognizable dog*, not a placeholder. See PRD §9–10.
