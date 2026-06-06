# pgap v2 — Composable Modular Creatures (design proposal)

Status: Proposal / RFC. Extends [PRD.md](../../PRD.md) and
[ARCHITECTURE.md](../ARCHITECTURE.md). Not yet implemented.

## 1. Motivation

v1 is **archetype-bounded** on purpose: `prop | quadruped | biped`, each a fixed
canonical rig. The PRD explicitly listed *"arbitrary open-vocabulary geometry
(a steampunk octopus-dragon)"* as a v1 **non-goal**.

v2 turns that non-goal on. The goal is to make the canonical example — the
octopus-dragon — and friends actually generate:

> octopus-dragon · mermaid · cthulhu · sphinx · beholder

The guardrail the user set: **"more modularization, but not too much."** We do
*not* build a fully general node-graph creature editor. We add a **curated library
of composable body-part modules** + a socket grammar, and let creatures be
*recipes* that assemble them.

## 2. The key observation

All five targets are **chimeras** — combinations of a small set of recurring
parts:

| Creature | = composition of modules |
|---|---|
| octopus-dragon | spine + draconic head + neck + legs×4 + wings×2 + **tentacles×6** + tail |
| mermaid | spine + humanoid head + neck + arms×2 + **fish-tail (serpent chain + fin)** |
| cthulhu | humanoid spine + arms×2 + legs×2 + wings×2 + head + **face-tentacles×6** |
| sphinx | **quadruped** spine + legs×4 + neck + **humanoid head** + wings×2 |
| beholder | **orb** body + central eye + mouth + **eyestalks×10** (radial) |

The recurring vocabulary is roughly: `spine, neck, head{humanoid|draconic|
lion|orb}, limb{leg|arm}, tail, tentacle, wing, fin, eyestalk, orb`. ~10–12
modules cover an enormous combinatorial space — the *feel* of open vocabulary
without unbounded generality.

## 3. What already composes (the reuse story)

The crucial enabler: **most of the v1 pipeline already operates on arbitrary
bone + blob sets.** It does not know or care that the capsules form a dog.

| Stage | Composes today? | Why |
|---|---|---|
| Geometry kernel | ✅ already | `geometry.py` smooth-mins a *list* of capsule/sphere blobs — any list |
| Skinning | ✅ already | distance-to-bone works for any bone set |
| UV | ✅ already | cylindrical unwrap is geometry-only |
| Texture | ✅ already | palette-driven (needs more coats: green/purple/scaled) |
| Assembler | ✅ already | emits any bones + anims + mesh + material |
| Determinism / budget back-off / validation | ✅ already | generic |
| **Skeleton (rigs)** | ❌ fixed | `_QUAD_RIG` / `_BIPED_RIG` are monolithic |
| **Part libraries** | ❌ fixed | `dog.py` hardcodes one creature's parts |
| **Animation** | ❌ fixed | clips target hardcoded bone names |

So v2 is **not** a rewrite. It refactors the *two* fixed stages (rigs, part
libraries) into a composable module system, plus modular animation. The heavy
stages stay unchanged. That is the "not too much" — we leverage the fact that the
hard parts already compose.

## 4. Core concept: a creature is a graph of socketed modules

### 4.1 Module

A reusable body-part unit bundling its rig, geometry, sockets, and motion:

```python
@dataclass(frozen=True)
class Module:
    kind: str                       # "spine" | "leg" | "tentacle" | "wing" | "orb" | ...
    bones: list[BoneTemplate]       # local-space rig (root-relative), module-prefixed names
    sockets: dict[str, Socket]      # named attach points this module *exposes*
    geometry: Callable              # (placed_bones, params, rng) -> list[Primitive]
    animate: Callable               # (placed_bones, params) -> list[ChannelContribution]
    params_schema: dict             # length, girth, segment count, curl, …
```

Examples:
- `spine` exposes sockets `front`, `back`, `top`, `underside`, `hip_l/r`,
  `shoulder_l/r`.
- `leg` consumes one socket, exposes `foot`. `tail`/`tentacle` are segment chains
  (param: `segments`, `curl`, `taper`) — the same chain module serves dragon
  tail, octopus arm, mermaid fish-spine.
- `head{variant}` exposes `crown`, `jaw`, `face_l/r` (for face-tentacles), `eye`.
- `wing` is a bone fan + membrane geometry. `fin` is a flat membrane at a tail
  tip. `orb` is a big sphere body exposing a **ring** of radial sockets + a
  `front` (eye/mouth) socket.

### 4.2 Socket

```python
@dataclass(frozen=True)
class Socket:
    position: vec3      # local to the host module
    orient: quat        # default outward direction for the attached module
    mirror: bool        # auto-instantiate a mirrored twin (bilateral limbs)
    ring: int | None    # if set, N evenly-spaced radial copies (beholder eyestalks)
```

`mirror` covers bilateral symmetry (paired legs/arms/wings) for free; `ring`
covers radial symmetry (beholder). These two patterns express every target.

### 4.3 Recipe (the "genome")

A small declarative spec — what an LLM authors, validated against the module +
socket grammar (fails closed on unknown module/socket):

```jsonc
{
  "name": "OctopusDragon",
  "seed": 12345,
  "skin": { "baseColor": "deep teal, violet underside", "scaled": true },
  "modules": [
    { "id": "body",  "kind": "spine", "variant": "draconic", "params": {"segments": 4} },
    { "id": "neck",  "kind": "neck",  "attach": "body.front", "params": {"segments": 3} },
    { "id": "head",  "kind": "head",  "variant": "draconic", "attach": "neck.front" },
    { "id": "wings", "kind": "wing",  "attach": "body.shoulder", "mirror": true },
    { "id": "legs",  "kind": "leg",   "attach": "body.hip", "mirror": true, "variant": "clawed" },
    { "id": "arms",  "kind": "tentacle", "attach": "body.underside",
      "count": 6, "params": {"segments": 6, "curl": 0.4} }
  ],
  "animations": ["idle", "swim"]
}
```

Build = resolve attachments (topo order), accumulate every module's placed bones
into one `Skeleton` and every module's `geometry` into one primitive list, then
feed the **unchanged** geometry → skin → uv → paint → texture → assemble pipeline.

## 5. Modular animation

The one genuinely new stage. Instead of clips hardcoding bone names, each module
contributes motion for *its own* bones, composed into named clips:

- `tentacle.animate(idle)` → travelling-wave sinusoid down its segments.
- `wing.animate(idle)` → slow flap; `(fly)` → strong flap.
- `tail.animate(idle)` → the v1 tail-wag, now a module behavior.
- `leg.animate(walk)` → the v1 gait swing, phase-assigned by the assembler so
  bilateral/quadruped legs alternate correctly.
- `eyestalk.animate(idle)` → independent slow sway per stalk (de-phased by index).

A named clip (e.g. `idle`) is the **sum of every module's contribution** to that
clip. Coordinated full-body locomotion (a sphinx walking *and* flapping) starts
as independent per-module motion; cross-module gait coordination is a later
refinement, not a blocker.

## 6. Mapping the targets (validation)

| Creature | Modules exercised | Stresses |
|---|---|---|
| sphinx | spine(quadruped) + leg×4 + neck + head(humanoid) + wing×2 | mixing body plans (quadruped + human head) |
| mermaid | spine + head(humanoid) + arm×2 + tail(serpent) + fin | chain-as-fish-tail; no legs |
| octopus-dragon | spine(draconic) + neck + head + wing×2 + leg×4 + tentacle×6 | many soft chains on one body |
| cthulhu | spine + arm×2 + leg×2 + wing×2 + head + face-tentacle×6 | tentacle cluster on a *head* socket |
| beholder | orb + eyestalk×10 + eye + mouth | **radial** sockets; no spine/limbs |

The beholder is the useful outlier — it forces the `ring` socket pattern and a
non-bilateral body. If the design handles all five, the module/socket grammar is
expressive enough.

## 7. What changes vs. what's reused

**New (the "more modularization"):**
- `modules/` — module library (`spine, neck, head*, leg, arm, tail, tentacle,
  wing, fin, orb, eyestalk`) with bones + sockets + geometry + animate.
- `assembly.py` — socket resolver: place modules (mirror/ring expansion), unique
  bone naming, accumulate bones + primitives; generalizes v1 `_assemble_bones`.
- `recipe.py` — recipe schema + grammar validator (fail-closed).
- modular animation composition in `animation.py`.
- richer palettes/skin (scales, iridescence keywords).

**Reused unchanged:** `geometry.py`, `skinning.py`, `uv.py`, `paint.py` (region
tint by dominant module), `texture.py`, `assemble.py`, the determinism spine,
budget back-off, manifest/import sidecar, and the whole `unreal-mcp-rx` handoff.

**Backward compatible:** the v1 `dog` / `biped` / `prop` become **preset recipes**
in the new system (quadruped = spine + 4 legs + neck + head + tail; dog adds its
part modules). `spec.archetype` stays as sugar that expands to a preset recipe, so
nothing downstream or in the proof lane changes.

## 8. Risks & mitigations

- **Self-intersection / topology.** Arbitrary module blends may overlap.
  *Mitigation:* SDF smooth-min unions are robust to overlap by construction; the
  existing largest-component + manifold gate + budget back-off already handle it.
- **Recognizability.** A composed cthulhu may read as "a weird tentacle monster,"
  not iconic cthulhu. *Mitigation:* set expectations (evocative, stylized, not
  licensed-accurate); invest art budget in head variants + skin.
- **Socket authoring is the real work.** Good sockets per module are the new "art
  budget" (analogous to the v1 part library). *Mitigation:* start with the ~10
  modules the 5 targets need; expand on demand.
- **Animation coordination.** Independent per-module motion first; full-body gait
  sync later.
- **Recipe explosion / nonsense.** *Mitigation:* the grammar validator fails
  closed; a capability report lists modules, sockets, variants — the same FR7
  pattern the LLM front-end already relies on.
- **Scale conventions.** Modules must share a canonical unit + attach scale.
  *Mitigation:* one reference height (as today), modules authored at it.

## 9. Proposed milestones

- **V2-M0 — Module/socket core.** `Module`, `Socket`, `assembly.py` resolver;
  re-express quadruped/biped/prop as preset recipes. **Exit:** existing dog/biped/
  rock regenerate from recipes with no visual regression (golden-SHA shift OK).
- **V2-M1 — Module library.** spine/neck/head-variants/leg/arm/tail/tentacle/
  wing/fin/orb/eyestalk. **Exit:** each module meshes + skins in isolation.
- **V2-M2 — Recipe schema + grammar validator + capability report.** **Exit:**
  fail-closed recipe validation; LLM-readable module/socket contract.
- **V2-M3 — Modular animation.** Per-module clip contributions composed. **Exit:**
  tentacle wiggle + wing flap + leg gait on one creature.
- **V2-M4 — Reference chimeras.** The five targets as recipes + variance corpus.
  **Exit:** all five generate valid, importable, recognizable-as-described meshes.
- **V2-M5 — NL → recipe.** Prompt → composition inference, fail-closed grammar.
  **Exit:** "a winged lion with a human head" → sphinx-like recipe → actor.

## 10. Open questions

1. Recipe authoring: how much does the LLM compose freely vs. pick from preset
   chimera templates with parameter overrides?
2. Sockets as data vs. code — declare in JSON, or compute from module geometry?
3. Region tint for chimeras: per-module palette overrides (teal body, violet
   tentacles) in the recipe `skin` block?
4. Do composite creatures need per-module `triBudget` allocation, or keep the
   single global budget + back-off?
5. Animation contract with `unreal-mcp-rx`: clip names are now composed — does the
   behavior lane bind by clip name (idle/swim) regardless of how it was built?
   (Likely yes — the seam is unchanged.)

## 11. Scope guardrail

"Modularization, but not too much": ship the **~10 modules** the five reference
creatures need and the two socket patterns (mirror, ring). Resist a general
graph-editor. Novelty comes from *composition within a curated module set* — the
same philosophy as v1 (novelty within archetypes), one level up.
