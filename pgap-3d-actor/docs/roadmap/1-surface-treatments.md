# Roadmap 1 — Surface treatments (scales / feathers / fur / chitin)

Status: **Implemented** (S0–S2). `material.surface` ∈ smooth/fur/scales/feathers/
chitin/bark drives a base-color pattern + a tangent-space normal map; the golden
retriever defaults to `fur`, live-verified in UE 5.7.4. Per-region surfaces (S3)
and a surface corpus sweep (S4) remain. The highest fidelity-per-cost upgrade.

## Motivation

Every creature is currently a smooth, untextured-detail blob with a flat-ish coat.
The single biggest visual win — for the least machinery — is to make the surface
*read* as scales, feathers, fur, or chitin **without changing the geometry**. The
mesh stays one smooth watertight SDF blob; a **base-color pattern + a normal map**
do the rest. Texture-side only: lightweight, deterministic, offline — fully
on-brand.

This makes *all existing creatures* look dramatically better at once.

**Reference case — the dog's coat.** The golden retriever is the clearest payoff:
today it's a smooth golden blob; with `surface: fur` it gains a directional, light-
catching coat and finally *reads* as a furry dog rather than a mannequin. "Make the
dog realistic" is, concretely, **fur** — so the dog is the acceptance creature for
S0–S2 (the S2 NL case is literally "a furry golden retriever" → `fur`).

## The idea

Add a **surface** treatment to the material:

```jsonc
"material": { "baseColor": "deep green", "surface": "scales", "roughness": 0.5 }
```

`texture.py` then synthesizes, for that surface:
- a **base-color** map = coat color modulated by the surface's pattern, and
- a **normal map** = surface relief (so light catches scales/feathers/fur),

both tiled over the existing UVs. The glTF material gains a `normalTexture`. UE
generates tangents on import, so no rig changes.

Surfaces to ship (curated): `smooth` (default, today's look), `scales`,
`feathers`, `fur`, `chitin`, `bark`. Later: per-region surface (scaly body +
feathered wings) via the v2 `--free` per-module skin hook.

## What's reused vs new

**Reused:** the UV stage, `paint.py` region tint, the assembler, determinism, and
the PNG encoder. Surfaces are just richer textures.

**New (all texture-side):**
- a small **procedural pattern library** — scales = hex/voronoi cells; feathers =
  overlapping shingle rows; fur = directional value-noise streaks; chitin =
  segmented plates; bark = ridged noise. Each produces a tiling **height field**.
- **height → normal map** (finite-difference gradient → RGB), encoded as a second
  PNG and embedded as the glTF `normalTexture`.
- assembler: emit `images[1]`, `textures[1]`, `material.normalTexture` (+ a
  `normalScale`).

## Milestones

- **S0 — Normal-map pipeline.** Emit a `normalTexture` in the glTF from a height
  field; one procedural pattern (scales). **Exit:** a scaled creature imports into
  UE with visible relief; deterministic; flat normal map for `smooth` (no change).
- **S1 — Surface library.** scales / feathers / fur / chitin / bark height+color
  generators. **Exit:** each reads distinctly in a viewer/UE — and the **golden
  retriever with `fur` reads as a furry dog** (the headline win).
- **S2 — Authoring hooks.** `material.surface` in spec + recipe; NL keywords
  (scaly/scaled → scales, feathered → feathers, **furry/fluffy → fur**, etc.);
  capability report lists surfaces. **Exit:** "a scaly green dragon" picks scales
  and "a furry golden retriever" picks fur, end to end.
- **S3 — Per-region surface.** A surface per module/region (body scales + wing
  feathers) via vertex-tagged regions or the `--free` per-module skin block.
  **Exit:** a mixed-surface creature.
- **S4 — Surface corpus.** Every surface × a host creature builds valid +
  deterministic; normal maps are valid PNGs. **Exit:** green.

## Risks & decisions

- **Tangents/seams.** Normal maps need tangents; UE computes them on import, but
  the cylindrical UV has a seam — keep patterns seam-tolerant (tileable in u).
  *Decision:* tileable patterns + accept a faint back seam (stylized).
- **How much a normal map sells it.** A normal map fakes relief but the silhouette
  stays smooth. *Decision:* good enough for stylized; if a surface needs real
  silhouette (big scales/spikes), that's a *geometry* slot (roadmap 2), not a
  surface.
- **Roughness/AO per surface.** Fur is matte, chitin glossy. *Decision:* per-
  surface roughness factor (and optionally an AO/roughness map later).
- **Per-creature vs per-region first.** *Decision:* per-creature in S0–S2;
  per-region in S3.

## Out of scope

Real displaced geometry, hair cards/strands, image-gen textures (parking lot).
