# Roadmap 4 — Part proportions (slim ↔ chubby)

A `girth` (a.k.a. "build") control that scales a part's **thickness independently of
its length** — make a creature lanky or stocky, a neck slim, legs chubby — without
touching the rig, the animations, or the topology.

This is the cheapest expressive axis in the whole system: girth is the **native
knob** of the geometry. Listed after 1–3 by priority, but it's small enough to land
opportunistically (the global cut is a few hours).

## Why it's nearly free

Every part's thickness is already **one number per bone**: the tapered-capsule
radius (`BoneSpec.radius_head` / `radius_tail` → the SDF blob radius in
`geometry.py`). Today the only related knob is `global_scale` (`g` in
`v2/assembly.py`), which scales **length and radius together** — so you can make a
creature bigger/smaller but *not* "chubby but short." Splitting girth out from size
is the whole feature.

It's low-risk because radius is what the marching-cubes field already consumes:

- **No topology risk** — re-meshes cleanly at any thickness (the opposite of
  faces/morph-targets, which fight the mesh).
- **Rig & animation untouched** — bones don't move; skin weights are
  distance-to-bone, so weights and clips are byte-identical. Purely visual.
- **Determinism preserved** — it's just a parameter.
- **Per-part plumbing already exists** — v3 threads a `params` dict into every
  module (`build_module(kind, variant, params)`); several parts already take a
  `radius` param (orb, eyeball, eyestalk). Per-part girth generalizes that.

## What's reused vs. new

- **Reused:** the entire pipeline. Radii already flow bone → SDF → mesh; the v3
  `params` channel already reaches every module; NL/recipe authoring is unchanged.
- **New:** one multiplier applied to radius (not length), a spec/recipe field, and
  a few NL keywords. No new geometry path, no new stage.

## Milestones

- **P0 — Global girth.** A `girth` float (default 1.0) on the spec/recipe; apply it
  to radius only where bones are emitted (`radius = r * g * girth` in
  `v2/assembly.py`, and the v1 equivalent in `skeleton.py::_assemble_bones`). NL
  words: `chubby`/`stocky`/`heavyset` (>1), `slim`/`lanky`/`skinny`/`lean` (<1).
  **Exit:** one creature renders visibly stockier/leaner at fixed height;
  deterministic; rig + clips unchanged; a fixture-SHA + "rig identical" test.
- **P1 — Per-part girth.** Honor a `girth` param on every module (one multiplier
  over its `BoneSpec` radii, applied centrally at bone-emit so authors don't repeat
  it). Expose on the recipe attachment `params` and in NL ("chubby legs", "slim
  neck"). **Exit:** a recipe sets different girth on two parts of one creature; the
  variant corpus gains a girth row.
- **P2 — Profile shaping (optional).** Head-vs-tail taper presets and an optional
  mid-bulge (belly, biceps) by perturbing `radius_head` vs `radius_tail` or adding a
  midpoint blob. **Exit:** a "pot-belly" and a "tapered" preset read as such. Mostly
  taste/tuning, not architecture.

## Risks / decisions

- **Smooth-min swallowing.** The blob fusion (`_SMIN_K = 0.07`) means a very slim
  part beside a fat one can get partially absorbed, and very chubby parts merge
  more. Mitigate with a **min-radius floor** and/or a per-part blend `k`; clamp the
  girth range (e.g. 0.6–1.6) so presets stay safe. Tuning, not engineering.
- **Budget.** Chubbier = more surface area = more tris; the existing resolution
  back-off already caps `triBudget`, so no new handling needed.
- **Scope split.** Keep `girth` strictly radius; keep `global_scale` strictly
  size. Two orthogonal knobs (build vs. height) is the point.

## Guardrail

Same as the rest of the roadmap: lightweight, deterministic, offline, stylized,
one geometry path. Girth adds a parameter, not a pipeline.
