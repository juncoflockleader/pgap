# Roadmap 4 — Part proportions (slim ↔ chubby)

Status: **P0 + P1 done** (P2 optional/deferred). A `girth` ("build") control scales a
part's **thickness independently of its length** — lanky or stocky, slim neck, chubby
legs — without touching the rig, the animations, or the topology. `girth` is a clamped
spec/proportions field *and* a universal per-part `params` key; the rig, weights
scheme, and clips are untouched (verified byte-identical for bones + clips), only the
SDF surface thickens. NL routes global build (`stocky`/`lanky`) and per-part
(`chubby legs`, `slim neck`). `test_proportions` gates it.

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

- **P0 — Global girth.** ✅ **done** — a clamped (0.6–1.6) `girth` in
  `spec.proportions` (with a `Spec.girth` accessor), applied to **radius only** at
  bone-emit in both `v2/assembly.py` and `skeleton.py` (the ground clamp keeps the
  base radius, so bone positions are *byte-identical*). NL: `stocky`/`chubby`/… (>1),
  `lanky`/`slim`/… (<1). **Exit:** ✔ — a biped renders visibly stockier/leaner at
  fixed height; deterministic; bones + clips byte-identical (`test_proportions`).
- **P1 — Per-part girth.** ✅ **done** — `girth` is a universal per-part `params` key,
  applied centrally in `registry.build_module` (one multiplier over a module's
  `BoneSpec` radii) so no author repeats it; accepted by the grammar on every kind
  and surfaced in the capability report (`universalParams`). NL: `chubby legs`,
  `slim neck` set per-part girth without making the whole creature stocky. **Exit:**
  ✔ — a recipe sets different girth on two parts; `test_proportions` covers it.
- **P2 — Profile shaping (optional).** ⏸ **deferred** (taste/tuning, not
  architecture) — head-vs-tail taper presets + an optional mid-bulge (belly,
  biceps). Can land opportunistically later.

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
