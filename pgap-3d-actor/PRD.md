# PRD: Procedural Generative Asset Pipeline (Architecture B)

Status: Draft v1
Owner: TBD
Related: README "Known blocker — 3D asset generation",
`docs/features/golden-retriever-real-deliverable-plan.md` (box-dog prototype),
the existing source-handoff / import / assembly / proof pipeline.

---

## 1. Summary

Build a deterministic, dependency-free system that turns a text spec (e.g. "a
golden retriever that wags its tail and barks") into a **game-ready, rigged,
animated, textured Unreal actor** — geometry, skeleton, skin weights,
animations, and PBR textures — generated **procedurally** rather than by an
external text-to-3D service.

This is "Architecture B" from the effort analysis. The deliberate trade: we own
the entire stack (offline, deterministic, reproducible, consistent art style) at
the cost of stylized — not photoreal — output. Text/image generative AI is used
only where it is actually good (concept/parameter inference, base-color
textures), never asked to produce 3D geometry, rigs, or animations.

The Unreal "last mile" (import, material authoring, Blueprint assembly, behavior,
runtime proof) is **already built** in this repo. This PRD scopes only the
**generation** stages that feed it.

## 2. Problem & motivation

`unreal-mcp-rx` can plan, import, assemble, author, and prove an actor in Unreal,
but it cannot produce the actual 3D content. Text + image generative models do
not output 3D geometry, skeletons, or animations. The current fallback is a
4-vertex placeholder or an external/Fab asset (manual, account-bound). To deliver
on "create an actor from a prompt," we need a 3D-generating component we control.

Two paths exist: (A) orchestrate external text-to-3D services, (B) build a
procedural generator. This PRD covers **B**, chosen when we want determinism, no
external dependencies/cost, a consistent stylized look across many generated
actors, and full control over rig/animation quality.

## 3. Goals / non-goals

### Goals
- Generate a **rigged, skinned, animated, textured** skeletal-mesh actor from a
  structured spec, exported as glTF (+ textures) that the existing bridge imports.
- **Skeleton-first** generation so rigging and skinning are correct *by
  construction*, not by a fragile post-hoc auto-rigger.
- **Deterministic**: same spec + seed -> byte-identical output. No network calls
  in the core path.
- **Archetype-routed**: cheap path for static props, richer path for quadrupeds,
  extensible to bipeds/characters.
- **Parametric & controllable**: proportions, breed/style traits, and animation
  set driven by named parameters an LLM (or human) can fill.
- Plug into the existing source-worker role + project-clone proof lane with no
  changes to the import/assembly/proof code.
- Quality bar: visibly recognizable as the requested creature (a dog reads as a
  dog), clean enough topology to import, shade, and animate without errors.

### Non-goals (v1)
- Photoreal output, fur/cloth simulation, facial rigs, morph targets.
- Replacing text-to-3D services for high-fidelity hero assets (that is path A).
- Arbitrary open-vocabulary geometry ("a steampunk octopus-dragon") — v1 covers a
  curated archetype taxonomy; novelty comes from parameters within archetypes.
- Auto-generating gameplay logic (the behavior graph already exists/Blueprint
  assembly is separate).

## 4. Users & use cases
- **The MCP agent**: fills a source-worker role's mesh/animation outputs from a
  spec during an interactive-component / asset-creation run.
- **A developer**: calls a CLI (`build_procedural_actor.py --spec spec.json`) to
  produce assets directly.
- **The LLM front-end**: converts a natural-language request into the structured
  spec (parameter inference), then invokes generation.

## 5. Key design insight: skeleton-first generation

The two hardest stages — rigging and skinning — are solved by *ordering*:

1. **Build the skeleton first** from a canonical, archetype-specific bone graph
   (e.g. quadruped: pelvis -> spine -> neck -> head; four legs; tail chain),
   scaled/proportioned by the spec.
2. **Synthesize geometry around the bones** using skeleton-driven implicit
   surfaces — metaballs / generalized cylinders ("limbs as tapered tubes swept
   along bone segments with a radius profile") blended into one smooth surface
   (SDF -> marching cubes), then decimated to a target tri budget.
3. **Skinning is then nearly free**: every surface vertex was generated from one
   or two bone segments, so weights come from distance-to-bone — no separate
   auto-rigger, no guesswork.
4. **Animations** are authored *once* on the canonical skeleton (idle, walk, run,
   tail-wag, bark pose) and retarget trivially because every generated mesh
   shares that exact bone topology — only proportions differ.

This converts "rig an arbitrary generated mesh" (hard/fragile) into "generate a
mesh around a known rig" (tractable/robust). It is the architectural crux of B.

## 6. System architecture

```
spec (JSON)                                 ┌────────────────────────────┐
   │  (LLM or human authored)               │  EXISTING (built, reused)  │
   ▼                                        │  - editor_asset_import     │
┌─────────────────┐                         │    (+ glTF flatten fix)    │
│ Archetype router│ prop / quadruped / biped│  - material authoring      │
└─────────────────┘                         │  - bp_author assembly      │
   │                                        │    (component refs, obj pins)│
   ▼                                        │  - pie_test_bp behavior     │
┌──────────────────────────────────────┐   │  - project-clone proof lane │
│ GENERATION (this PRD)                 │   └────────────────────────────┘
│  1. Skeleton builder (canonical rig)  │                ▲
│  2. Geometry kernel (SDF/metaballs    │                │ glTF + textures
│     around bones) -> mesh             │                │ (source-worker role)
│  3. Skinning (distance-to-bone)       │ ───────────────┘
│  4. UV layout (per-archetype atlas)   │
│  5. Texture synth (image-gen + procedural)
│  6. Animation retarget (canonical clip library)
│  7. glTF assembler + manifest/import sidecar
└──────────────────────────────────────┘
```

### Modules
1. **Archetype router** — classifies the spec, selects the rig template, part
   library, UV atlas, and animation set.
2. **Skeleton builder** — instantiates the canonical bone graph, applies
   proportion parameters (leg length, body length, neck, tail length, scale),
   emits joints + bind poses + bone names that match the animation library.
3. **Geometry kernel** — pure-Python (numpy) SDF field of capsule/blob primitives
   placed along bones (body, head, snout, ears, legs, tail), smooth-min blended,
   marching-cubes meshed, decimated to a tri budget, normals computed.
4. **Skinning** — per-vertex weights from distance to the generating bone
   segment(s) (1–4 influences), normalized.
5. **UV layout** — fixed per-archetype atlas regions (body, head, legs, tail) so
   textures are paint-targetable and deterministic.
6. **Texture synth** — base color from an image-gen call painted into the atlas
   regions (the only optional online step; cached + seeded) with a procedural
   fallback; procedural roughness/normal/AO.
7. **Animation retarget** — load canonical clips, scale keyframes to the
   generated proportions, emit glTF animation channels (e.g. tail-wag for the
   wiggle behavior).
8. **glTF assembler** — writes a single glTF (mesh + skin + animations) plus
   textures and the `*.import.json` metadata sidecar (target skeleton, tail bone,
   skeleton policy) the source-handoff pipeline already consumes.

## 7. Inputs & outputs

### Input: actor spec (JSON)
```jsonc
{
  "archetype": "quadruped",          // prop | quadruped | biped
  "species": "dog",
  "style": "stylized_low_poly",
  "seed": 12345,                      // determinism
  "proportions": { "bodyLength": 1.0, "legLength": 1.0, "neck": 0.8, "tail": 1.2, "heightCm": 60 },
  "traits": { "ears": "floppy", "snout": "medium", "tail": "feathered" },
  "material": { "baseColor": "warm golden, darker ears", "fur": true },
  "animations": ["idle", "walk", "tail_wag", "bark_pose"],
  "triBudget": 8000,
  "targetSkeletonName": "SKEL_GoldenRetriever",
  "tailBone": "tail_01"
}
```

### Output
- `<Name>.gltf` — skeletal mesh + skin + requested animations on the canonical rig.
- `<Name>_BaseColor.png` (+ optional normal/roughness).
- `<Name>.import.json` — import metadata sidecar (target skeleton, tail bone,
  skeleton policy) matching the existing source-handoff contract.
- `manifest.json` — provenance: spec hash, seed, generator version, file SHAs,
  license note ("procedurally generated, original").

## 8. Functional requirements
- FR1: Deterministic — identical (spec, seed) -> identical bytes; core path makes
  no network calls (texture image-gen is optional, cached, and has a procedural
  fallback).
- FR2: Output imports cleanly via the existing `editor_asset_import` and produces
  SkeletalMesh + Skeleton + AnimSequence(s) with no import errors.
- FR3: Generated skeleton bone names match the animation library and the
  `import.json` sidecar (so the tail-wiggle behavior binds without retargeting).
- FR4: Topology is manifold, watertight-enough to shade, within the tri budget,
  with valid UVs in [0,1].
- FR5: Skin weights normalized, <=4 influences/vertex, no unweighted vertices.
- FR6: Slots into the source-worker role and the project-clone proof lane,
  producing a passing import + assembly + behavior proof (the golden retriever as
  the reference acceptance case).
- FR7: A spec-validation + capability report (what archetypes/traits/anims are
  supported) so the LLM front-end fails closed on unsupported requests.

## 9. Quality bar & acceptance
- **Recognizability**: a neutral viewer labels the rendered output as the
  requested creature ("a dog") in a blind check on a small panel.
- **Import**: zero import/compile errors; SkeletalMesh + Skeleton + anims created.
- **Animation**: the tail-wag visibly moves the tail bone; idle/walk loop cleanly.
- **Reference case**: regenerate the golden retriever and re-run the existing
  project-clone proof lane to green (import + material + assembly + bark/tail-wag
  PIE), with a *recognizable dog* instead of the box placeholder.
- **Variance**: 10 random seeds of the same species all import and read as that
  species (no degenerate/exploded meshes) — tracked as a golden corpus.

## 10. Milestones (phased)

- **M0 — Geometry kernel & determinism.** SDF/metaball-around-bones kernel,
  marching cubes, decimation, normals, deterministic seeding, glTF export. Exit:
  a smooth quadruped blob that imports and clearly beats the box dog.
- **M1 — Canonical quadruped rig + skinning.** Bone graph, proportion params,
  distance-to-bone skinning. Exit: animatable skeletal mesh, weights valid.
- **M2 — Dog parametric library.** Part library (ears/snout/tail variants),
  breed/proportion params; the golden retriever as the reference spec. Exit: a
  recognizable dog.
- **M3 — Animation library + retarget.** Canonical clips (idle/walk/run/tail_wag/
  bark_pose) authored on the rig, proportion-retargeted into glTF channels. Exit:
  tail-wag drives the existing behavior; locomotion loops.
- **M4 — UV + texture synth.** Per-archetype atlas, image-gen base color (cached,
  fallback), procedural roughness/normal, material binding via the existing
  material authoring. Exit: golden fur material, not flat color.
- **M5 — Proof integration.** Wire into the source-worker role + project-clone
  proof lane; regenerate the golden retriever and pass the lane green. Exit: FR6.
- **M6 — Other archetypes.** Static-prop fast path (no rig); biped/character path
  (reuse skeleton-first). Exit: a prop and a simple biped generated.
- **M7 — LLM front-end + corpus.** NL spec -> parameter inference with
  validation/capability report; golden corpus + variance regression proofs. Exit:
  end-to-end "prompt -> playable actor" demo + regression suite.

## 11. Determinism, provenance, licensing
- Single seeded RNG threaded through every stage; no wall-clock/UUID/order
  nondeterminism. CI re-runs a fixture spec and diffs the output SHA.
- Each output carries a manifest: spec hash, seed, generator version, per-file
  SHA-1, and a clear "procedurally generated original work" license note (this is
  also why B is attractive — no third-party asset rights to clear).

## 12. Risks & mitigations
- **R1: Stylized ceiling.** SDF blobs may look generic. *Mitigation*: invest the
  art budget in the part library + textures + animation; set expectations
  (stylized, not photoreal); keep path A available for hero assets.
- **R2: Quadruped animation authoring cost.** Hand-authoring good canonical clips
  is real work. *Mitigation*: start with a minimal set (idle, wag) for the
  reference case; expand; consider sourcing CC0 quadruped mocap retargeted once to
  the canonical rig.
- **R3: Topology pathologies** (non-manifold, holes from marching cubes).
  *Mitigation*: post-mesh cleanup (largest-component, hole-fill, manifold check)
  as an FR4 gate; reject + reseed on failure.
- **R4: Marching-cubes performance in pure Python.** *Mitigation*: numpy-vectorize;
  allow an optional compiled accelerator behind the same deterministic interface;
  cache by spec hash.
- **R5: Scope creep across archetypes.** *Mitigation*: ship the quadruped/dog
  reference case end-to-end (M0–M5) before generalizing (M6+).

## 13. Dependencies & constraints
- Core: pure Python + numpy (determinism, no UE needed for generation). glTF
  written by hand (the repo already does this) or via a vetted writer.
- Optional: an image-generation endpoint for base color (cached, fallback to
  procedural) — the only non-deterministic input, isolated and seeded.
- Reuses, unchanged: `editor_asset_import` (glTF flatten), material authoring,
  `bp_author` (component refs + object-pin defaults), `pie_test_bp`, the
  project-clone proof lane.

## 14. Success metrics
- % of generated specs that import + assemble + pass the proof lane (target: >95%
  for supported archetypes).
- Blind recognizability rate for the reference species (target: high).
- Time-to-asset (spec -> imported actor) and determinism (SHA stability across
  runs/machines).
- Reduction in reliance on placeholder/Fab assets for in-house content.

## 15. Open questions
- Canonical animation sourcing: hand-author vs retarget CC0 quadruped mocap?
- How much open-vocabulary do we want in v1 vs a fixed archetype taxonomy?
- Texture path: commit to an image-gen provider, or ship procedural-only first?
- Where does the LLM parameter-inference live — in the MCP server or a separate
  service — and how do we validate/clamp its parameters?

## 16. Appendix — existing proof points in this repo
- The box-dog prototype (`scripts/build_golden_retriever_assets.py`) already does
  a primitive version of skeleton + skinned mesh + tail-wag glTF, hand-written and
  deterministic — the seed of the geometry/skeleton/skin/animation stages.
- The bridge already imports that glTF (flatten fix), authors the fur material,
  assembles `BP_GoldenRetriever`, and PIE-proves bark + AnimSequence-driven tail
  wiggle. The "last mile" this PRD feeds is therefore demonstrated working; only
  the generation quality is being uplifted from "box" to "recognizable creature."
