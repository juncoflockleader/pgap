# PRD: pgap-gear — Procedural Gear Asset Pipeline (pgear)

Status: **v1 implemented.** Rigid static-mesh **weapons + shields** composed from a
module kit, with named variants, a freeform material palette, a preview render, and
the engine handoff. Part of the `pgap` monorepo; sibling of `pgap-3d-actor`,
`pgap-sound`, `pgap-landscape`, `pgap-city`; shares their architecture, determinism,
and `unreal-mcp-rx` handoff.

---

## 1. Summary

Turn a gear spec (a **template** + **variant** + freeform **material** + size +
seed) — or a natural-language prompt — into **game-ready equipment**: a
multi-material **static-mesh glTF** + a preview PNG + an import sidecar (pivot,
grip socket, materials) + a manifest, generated **deterministically and offline**.

"Architecture B" for gear: don't ask a model to *model* the weapon — **assemble it
from a curated module kit** (blade + guard + grip + pommel; haft + head; …) the way
`pgap-3d-actor` composes creatures. pgap-gear owns *what the piece is and how it's
built*; `unreal-mcp-rx` owns the engine last mile (import, material assignment,
socket-attach/equip, proof).

## 2. Why rigid first

Most gear is a **rigid static mesh** (no skin) — the simplest path in the family.
Weapons (swords, axes, spears, maces, staves, bows) and shields are hard-edged, so
they're built from explicit flat-shaded primitives (tapered boxes, prisms) and
concatenated — no SDF/marching-cubes kernel needed. Worn apparel/armor that deforms
with a character (skinned to a `pgap-3d-actor` rig) is the harder, later path.

## 3. Goals / non-goals

### Goals
- A **module kit + recipe grammar**: part primitives (blade/guard/grip/pommel,
  haft/head, limbs, plate/boss) → per-template recipes with named **variants**.
- **Deterministic:** same spec + seed → byte-identical mesh + sidecar (fixture-SHA).
- **Material-routed:** a freeform material string maps to palette slots
  (metal / grip / accent / wood); flat per-part PBR materials, no textures needed.
- **Composable & family-consistent:** own glTF/PNG writers, capability report,
  fail-closed validator, NL `--describe`, `--handoff` roles — like the siblings.
- A **preview render** (headless software rasterizer) so a piece is legible offline.
- An **import sidecar** carrying pivot, a `grip` socket (hand-attach), bounds,
  category, and the material list, so the bridge can equip it.

### Non-goals (v1)
- **Skinned/worn apparel & armor** (cloth/plate that deforms with a body) — the
  later path; v1 is rigid held/equipped pieces.
- **The engine actions** — import, material/lighting authoring, socket-attach to a
  character, PIE proof. That is `unreal-mcp-rx`'s last mile.
- **High-poly / photoreal hero pieces.** Stylized low-poly, owned, offline.
- **Enchantment FX, animation, breakage.** Static meshes in v1.

## 4. System architecture

```
gear spec ({template, variant, material, size, seed})  — or a prompt via nl
  → seeded params (geometry is a pure function of scale × variant × materials)
  → recipe = the template's part stack (items.py): blade/guard/grip/… along +Y
  → MeshBuilder: flat-shaded primitives tagged by material slot (geom.py)
  → multi-material static-mesh glTF (one primitive per material)  +  preview PNG
  → import.json sidecar (pivot, grip socket, bounds, materials) + manifest
  → (--handoff) unreal-mcp-rx source bundle: GearMesh / GearImport / GearPreview
```

### Modules
- **`geom`** — the rigid-mesh kernel: `MeshBuilder` + frustum/box/prism primitives,
  flat normals, material tags.
- **`items`** — part helpers (blade/grip/pommel/haft) + one builder per template.
- **`registry`** — templates → builder/variants/scale/category/material palette.
- **`materials`** — the PBR material library + freeform-string → slot resolver.
- **`gltf` / `render` / `pngio`** — multi-material glTF, headless preview, PNG.
- **`spec` / `capabilities` / `nl`** — schema + fail-closed validator, machine
  report, prompt→spec.

### v1 templates
| template | variants | category |
|---|---|---|
| sword / greatsword / dagger | straight, curved, leaf | weapon |
| katana | uchigatana, wakizashi, great, nodachi | weapon |
| thrusting_sword | rapier, estoc, heavy, stitcher | weapon |
| twinblade | balanced, peeler, leaf, ornate | weapon |
| axe | battle, double, crescent, cleaver | weapon |
| hammer | warhammer, club, pick, spiked, great | weapon |
| spear | leaf, pike | weapon |
| halberd | axe, glaive, bill, crescent, banner | weapon |
| reaper | scythe, grave, halo, winged | weapon |
| mace | flanged, round | weapon |
| flail | spiked, chainlink, round | weapon |
| staff | gem, ornament | weapon |
| sacred_seal | finger, order, clawmark, spiral | catalyst |
| bow | recurve, longbow | weapon |
| greatbow | great, golem, horn | weapon |
| crossbow | light, heavy, repeating, pulley | weapon |
| torch | flame, ghostflame, sentry, wire | tool |
| claw | hook, talon, beast | weapon |
| fist | caestus, spiked, katar | weapon |
| perfume_bottle | round, faceted, fire, lightning, poison | tool |
| shield | round, kite, heater, buckler, great, tower, palisade, thrusting | armor |

Material slots: **metal** (steel/iron/bronze/gold/silver/obsidian/bone/dark steel/
verdigris/crystal), **grip** (leather/wood/cloth/wire), **accent**
(gold/bronze/silver/gems/crystal/flame/holy), **wood**.

## 5. Inputs & outputs

**Spec** `{ name?, template, variant|"auto", material:"freeform", size:
small|normal|large|huge, seed }`. `validate_spec` fail-closes on an unknown
template; an unknown variant/size warns and falls back.

**Output (`--out`)**: `SM_<name>.gltf` (multi-material static mesh) ·
`<name>_Preview.png` · `<name>.import.json` (pivot, sockets, bounds, materials) ·
`manifest.json`. With `--handoff`: the source bundle (GearMesh/GearImport/
GearPreview roles).

## 6. Quality bar & acceptance

- **Determinism** — same (spec, seed) → byte-identical files (fixture-SHA test).
- **Validity** — finite geometry, unit normals, every triangle materialed, within a
  tri budget; the glTF imports as a static mesh with one material per part.
- **Legibility** — a human/agent reads the template + materials from the preview (a
  curved iron sword looks like one).
- **Engine round-trip** — the bridge imports `SM_<name>.gltf`, assigns the
  materials, attaches it at the `grip` socket, and a capture reads as the intended
  piece.

## 7. Milestones

- **G0 — kit + weapons.** ✅ Geom kernel, item recipes, registry, multi-material
  glTF, preview render, spec/validator, NL, capabilities, CLI, manifest/handoff,
  tests. Nine templates (sword/greatsword/dagger/axe/spear/mace/staff/bow/shield).
- **G1 — breadth & detail.** ✅ Elden Ring-inspired rigid breadth pass:
  katana/rapier-like thrusting swords/halberds/reapers/twinblades/flails/greatbows/
  crossbows/torches/claws/fists/seals/perfume bottles and expanded shield classes.
  Remaining detail work: per-part jitter, fullers/serrations, richer gem accents,
  and a fixture corpus per template.
- **G2 — worn apparel/armor.** Skinned pieces (helm/cuirass/cloak) attached to a
  `pgap-3d-actor` skeleton — the deformable path.
- **G3 — engine proof lane.** Bridge imports + materials + socket-equip + PIE proof.

## 8. Determinism, provenance, licensing

One pure-function build path; geometry is a deterministic function of (scale,
variant, materials) — no wall-clock/UUID/ordering nondeterminism. Manifest records
spec hash, seed, per-file SHA-1, and a license note. Output is original procedural
work.

## 9. Relationship to siblings & unreal-mcp-rx

- **pgap-3d-actor** provides the creatures that wield the gear (and, later, the rigs
  worn apparel skins to).
- **unreal-mcp-rx** owns every engine action: import the static mesh, assign
  materials, attach at the `grip` socket / equip on a character, light, and prove in
  PIE. pgap-gear ships files + a role-tagged manifest.
