# pgap roadmap

Where pgap grows next. The architecture front-loaded the hard part (one
body-agnostic SDF → skin → uv → texture → animate pipeline), so growth is mostly
**data, not machinery**. These are ordered by fidelity-per-cost.

**Build order: 1 → 2 → 3.**

| # | Feature | One line | New machinery? | Doc |
|---|---|---|---|---|
| 1 | **Surface treatments** | scales / feathers / fur / chitin via texture + normal map (mesh stays a smooth blob, but *reads* detailed) | Small (texture-side only) | [1-surface-treatments.md](1-surface-treatments.md) |
| 2 | **Library flywheel + bestiary** | more bases / slots / variants / named presets, made *contributable*, plus a rendered catalog | Almost none (data) | [2-library-flywheel-and-bestiary.md](2-library-flywheel-and-bestiary.md) |
| 3 | **v4 — faces** | face textures + a small jaw/eye **bone** rig + expression clips | Moderate; **no morph targets** | [3-v4-faces.md](3-v4-faces.md) |
| 4 | **Part proportions** | a `girth` knob (slim ↔ chubby), per part, independent of size | Tiny (one radius multiplier) | [4-part-proportions.md](4-part-proportions.md) |

## Why this order

1. **Surface treatments first** — biggest visual upgrade for the least work, and
   it makes *every existing creature* look better at once. Pure texture-side, fully
   on-brand (lightweight, deterministic, offline).
2. **Library flywheel second** — once creatures look good, widen the bestiary; the
   payoff is breadth, and the work is small isolated modules (ideally
   community-contributable, gated by the corpus test).
3. **Faces last** — highest value but highest uncertainty (stylized capsule blobs
   are the hardest place to put a readable, expressive face). Do it once the look
   and breadth are strong, and keep it lightweight (bones + texture, never morph
   targets).

## Guardrail (applies to all three)

Stay **lightweight, deterministic, offline, stylized**. Growth is curated, not
open-vocabulary. Anything that would force a second geometry path, a trained
model in the core, or break the single-watertight-mesh / determinism guarantees
goes to the parking lot, not the roadmap.

## Parking lot (deliberately deferred)

- **Flat/quad primitive** for crisp thin parts — decided against (v3, decision A).
- **Morph targets / blendshapes** — fight marching-cubes topology; faces use bones
  instead (see roadmap 3).
- **Image-gen base-color textures** — the one PRD-sanctioned online step (cached,
  procedural fallback); revisit only if procedural surfaces (roadmap 1) fall short.
- **Real quadric decimation / LODs** — currently resolution back-off; fine for now.
- **Godot / Unity bridges** — the engine-neutral glTF makes this cheap later; not
  a generator concern.
- **Retarget to the UE Mannequin skeleton** — for animation-library reuse; a
  consumer-side concern.
