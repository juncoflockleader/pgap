# pgap — Architecture & Workflow

How pgap works end to end, how it pairs with the `unreal-mcp-rx` engine bridge,
and why it deliberately needs no model inference in its core. Companion to
[PRD.md](../PRD.md) (what/why) and [DESIGN.md](../DESIGN.md) (how, per stage).

---

## What pgap is

A deterministic, dependency-light **procedural content generator**: it turns a
structured spec (or a natural-language prompt) into a game-ready, rigged, skinned,
animated, textured actor exported as glTF — without asking any model to produce
3D geometry, rigs, or animations.

## The full pipeline

```
prompt / spec ─▶ validate ─▶ [ one seeded RNG threaded through everything ]
                                │
        ┌───────────────────────┴───────────────────────────────────┐
        ▼                                                            ▼
   ARCHETYPE ROUTER  (prop | quadruped | biped)
        │
        ▼
   1. SKELETON   canonical rig as data, proportioned from the spec      (skeleton.py)
   2. PARTS      extra SDF blobs (dog ears/snout/tail; or prop shapes)  (parts.py, archetypes/)
   3. GEOMETRY   capsule SDF + smooth-min → voxel field → marching cubes (geometry.py)
                 → cleanup → normals   (+ budget back-off → triBudget is a hard cap)
   4. SKINNING   per-vertex weights from distance-to-bone               (skinning.py)
   5. UV         cylindrical unwrap                                     (uv.py)
   6. PAINT      per-vertex region tint (darker ears, cream chest…)     (paint.py)
   7. TEXTURE    procedural fur base color (palette × value noise)      (texture.py)
   8. ANIMATE    canonical clips as joint-rotation tracks              (animation.py)
        │
        ▼
   9. ASSEMBLE   one glTF (mesh + skin + anims + PBR material + texture) (assemble.py)
                 + <Name>.import.json sidecar + manifest.json (spec hash, SHAs, license)
        │
        ▼  (optional, M5)
  10. HANDOFF    role-named bundle (SK_/A_/T_ files + v1 manifest)       (handoff.py)
        │
        ▼
  11. UNREAL     editor_asset_import → SkeletalMesh/StaticMesh + Skeleton +
                 AnimSequences + Texture + Material → BP assembly → bark/tail-wag PIE
```

**Stage 0 — intent → spec.** Either the spec JSON is authored directly, or
`nl.prompt_to_spec("a tall black dog…")` infers it from a sentence.
`capabilities.validate_spec` then checks it and **fails closed** — unsupported
archetypes are rejected, out-of-range numbers clamped (FR7).

**The determinism spine.** One `numpy.random.Generator(PCG64(seed))` is created
from the spec seed and threaded explicitly through every stage; it is never
re-seeded. Stages 1–9 are pure functions; I/O happens only at the edges (read
spec, write glTF/PNG). That is what makes *same (spec, seed) → byte-identical
output* true on any machine. The 60-test suite asserts both mesh validity and
SHA stability.

Everything from stage 1 on is **plain numpy** — capsule distance fields, a
hand-rolled marching-cubes table, inverse-distance skin weights, sinusoidal joint
rotations, value-noise textures. No services, no network in the core path.

## The working model: pgap + unreal-mcp-rx

Two complementary halves of one pipeline — a clean split of *make the content* vs
*make it work in the engine*:

```
  LLM / agent
      │  writes the spec (or a prompt)
      ▼
 ┌─────────────┐   files on disk    ┌───────────────────┐   live editor
 │    pgap     │ ─────────────────▶ │  unreal-mcp-rx    │ ───────────────▶  playable
 │ (generator) │  glTF + textures   │   (engine bridge) │  import, material,   UE actor
 │  OFFLINE    │  + import.json     │   LIVE / online   │  Blueprint, PIE
 └─────────────┘  + handoff manifest└───────────────────┘  proof, rollback
   "where does the 3D                "make it a working actor
    come from?"                       in Unreal"
```

- **pgap** — the content generator. Deterministic, offline, **engine-agnostic**.
  Emits standard glTF + PNG + manifest. Knows nothing about Unreal.
- **unreal-mcp-rx** — the *last mile*. An MCP server driving a live UE editor:
  import, material authoring, Blueprint assembly, behavior, PIE proof, rollback
  evidence. Knows nothing about how to make 3D.

The **seam** between them is the M5 source-handoff contract: the role-named
`SK_/A_/T_` files plus the `game.interactive_component_agent_source_manifest.v1`
manifest. pgap fills the "source-worker role"; the bridge's project-clone proof
lane consumes it.

### Do you need both?

| Goal | Need |
|---|---|
| A 3D **asset file** (glTF) — Blender, Godot, three.js, Unity, any engine | **pgap alone** |
| A **playable, imported, Blueprint-assembled, PIE-proven Unreal actor** | **both** |

They pair because each closes the other's gap:
- `unreal-mcp-rx` without pgap hits its own "known blocker" — it can plan / import
  / assemble / prove, but has no real 3D to feed in (falls back to a box
  placeholder). That blocker is why pgap exists.
- pgap without the bridge gives correct files but no automated in-engine assembly
  or runtime proof.

Together: **prompt → spec → content → imported, assembled, proven actor.**

**Engine-neutrality.** pgap output is plain glTF + PNG; only the small
`import.json` sidecar is Unreal-flavored (and optional). A Unity-MCP or Godot-MCP
bridge could consume the same output. The generator is the reusable core; **the
bridge is swappable per engine.**

## Why it needs no LLM backend

The core design insight ("Architecture B" in the PRD):

> Text and image models cannot reliably output 3D geometry, skeletons, or
> animations. They are good at language and pixels, not meshes and rigs.

So pgap deliberately does **not** ask a model to make the 3D. Shape comes from
SDF + marching cubes, skinning from distance-to-bone, animation from math curves,
texture from noise — algorithms, not inference.

That leaves exactly one job an LLM is good at: turning *"a small golden retriever
that wags its tail"* into structured parameters (a spec). That is a small
**text → JSON** mapping. When an LLM agent uses pgap, its whole role is to fill
the spec (reading the capability report to stay in bounds); then it calls the
deterministic generator. The mapping is so small that pgap ships a deterministic
keyword version (`nl.py`) that works **with no model at all**.

| Keeping the model out of generation gives up | …and gains |
|---|---|
| Photorealism (output is **stylized**) | Determinism — same spec+seed → identical bytes |
| Open vocabulary (**archetype-bounded**) | Offline, free, instant; no API latency/cost/limits |
| | Consistent art style at scale; clean licensing; **testable** |

The only place a model may optionally plug in is the base-color texture
(image-gen for fur) — isolated, cached, seeded, with a procedural fallback — so
the core stays offline and deterministic regardless.

**Mental model:** the LLM decides *what* to make (the spec); pgap deterministically
computes *how* to build it. The intelligence is in the parameters, not the pixels.

## Why it's lightweight

~15 modules of pure Python + numpy — surprisingly small for "3D generation,"
because it is **algorithmic, not learned**:

- A skeleton = a few dozen lines of bone coordinates (data).
- Geometry = a handful of SDF formulas + the fixed 256-row marching-cubes table.
- Skinning = one distance computation. Animation = sine waves on joints.
- Texture = value-noise × a color.

The "knowledge of a dog" is encoded as **code + small authored data tables** (rig,
part library, palette) — kilobytes — not billions of trained parameters. You only
need the *idea* of a dog (which bones, which blobs, what proportions), not a
learned distribution over all dogs.

It leans on numpy for the vectorized math and writes glTF directly — no graphics
engine, no mesh library, no ML framework. "Dependency-light" is a stated core
principle, not an accident.

## Pointers

- [PRD.md](../PRD.md) — product requirements, milestones M0–M7.
- [DESIGN.md](../DESIGN.md) — per-stage algorithms and data structures.
- [docs/milestones/](milestones/) — M0–M7 implementation plans + exit criteria.
- [docs/design/v2-modular-creatures.md](design/v2-modular-creatures.md) — proposal
  to extend beyond fixed archetypes to composable, chimeric creatures.
