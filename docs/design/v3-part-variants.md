# pgap v3 — Part Variants & Library Enrichment (design proposal)

Status: Proposal / RFC. Extends [v2-modular-creatures.md](v2-modular-creatures.md)
and [ARCHITECTURE.md](../ARCHITECTURE.md). Not yet implemented.

## 1. Motivation

v2 made creatures *compositional* — a creature is a graph of socketed modules.
But each module kind is still **one fixed form**. That's underspecified:

> When we say a **wing**, is it a bat wing, a swan wing, or a hang-glider wing?
> When we say a **horn**, is it a unicorn horn, a ram's curl, deer antlers, or a
> rhino's nasal horn?

A "wing" is a *slot*; "bat" / "feathered" / "membrane" is the *form*. v3 adds that
second axis — **part variants** — and grows the library with the anatomy creatures
actually need (horns, tusks, hooves, claws, manes, …).

This is the same philosophy one level deeper: v1 = novelty within archetypes,
v2 = novelty within a module set, **v3 = novelty within each part**.

## 2. The two axes

```
                 kind  (the slot — WHAT body part)
                  │
   wing ──────────┼── variant: bat | feathered | membrane/glider | insect
   horn ──────────┼── variant: unicorn | antler | ram | bull | rhino
   tail ──────────┼── variant: serpent | dragon | fish | lion-tuft | scorpion
   head ──────────┼── variant: humanoid | draconic | lion | avian | cephalopod
   ear  ──────────┼── variant: floppy | pointy | bat | long
   leg/foot ──────┼── variant: paw | hoof | talon | digitigrade
```

`kind` chooses the socket-compatible slot and the broad role; `variant` chooses
the geometry/bones authored into it. Sockets a part exposes are (almost always)
variant-independent, so **variants are internal to a module** — assembly,
skinning, UV, texture, and animation are all unchanged.

## 3. Data model (additive)

### Recipe
A module entry gains an optional `variant`:
```jsonc
{ "id": "wings", "kind": "wing", "variant": "feathered", "attach": "body.wings", "mirror": true }
```
Omitted → the kind's default variant (keeps every v2 recipe valid).

### Registry
`MODULE_REGISTRY[kind]` becomes a small variant table:
```python
ModuleKind(
    default = "bat",
    variants = {                       # name -> (params -> Module)
        "bat":       _wing_bat,
        "feathered": _wing_feathered,
        "membrane":  _wing_membrane,
        "insect":    _wing_insect,
    },
    params = ("span", "droop"),
)
build_module(kind, variant=None, params=None)
```

### Grammar (fail-closed)
`validate_recipe` gains one rule: if `variant` is given it must exist for that
`kind` (else error); an unknown variant **fails closed**, an omitted one warns +
uses the default. Everything else from v2's validator is unchanged.

### Capability report
`modules[kind]` gains `variants: [names]` and `defaultVariant`. The LLM now sees
not just "wing" but "wing: bat | feathered | membrane | insect".

### NL inference
Keyword → variant, layered on top of v2's kind detection:
`bat → bat`, `swan|feathered|bird|angel → feathered`, `glider|membrane|leathery →
membrane`; `antler|deer|stag → antler`, `ram|curled → ram`, `bull|buffalo|ox →
bull`, `unicorn|spiral → unicorn`, `rhino → rhino`. "a deer-antlered dragon with
feathered wings" → head:draconic + horn:antler + wing:feathered.

## 4. Geometry approach

Variants are still **capsule-SDF composable** — the same stylized bone-fan trick,
just authored per form. Examples:

- **wing/bat** = arm + finger fan + webbing (today's wing).
- **wing/feathered** = arm + a row of tapered "feather" capsules along the
  trailing edge.
- **wing/membrane (glider)** = a stiff, near-flat delta of a few capsules.
- **horn/unicorn** = one straight tapering capsule (slight twist).
- **horn/antler** = a branching bone tree (main beam + tines — explicit
  parent/child bones within the module).
- **horn/ram** = a curled chain (segments sweeping around).
- **horn/bull** = two capsules sweeping out then up.
- **tusk** = a paired curved capsule from the jaw. **hoof** = a blocky rounded
  cap at a leg tip. **claw** = a few small splayed capsules. **mane** = a ridge of
  capsules along the neck.

**Fidelity note — DECIDED: stay stylized (capsule-SDF only).** Thin features
(feathers, membranes, fins) read as "rounded" under capsule-SDF. A flat/quad
primitive would sharpen them but would break the single-watertight-mesh model
(two geometry paths, relaxed manifold gate, special-cased skin/UV/normals) — too
heavy for a deliberately lightweight project. **We keep one unified SDF mesh and
author variants to lean into it** (separated feathers with gaps, thin-ish fans,
lower blend-`k`), accepting a charming low-poly chunkiness as on-style. The flat
primitive stays parked unless a future need justifies the complexity.

## 5. Library enrichment (the curated set)

| Slot (kind) | Variants to ship |
|---|---|
| `wing` | bat, feathered, membrane/glider, insect |
| `horn` *(new)* | unicorn, antler, ram, bull, rhino |
| `tusk` *(new)* | boar, elephant, walrus |
| `foot`/`leg-tip` *(new)* | paw, hoof, talon |
| `claw` *(new)* | small splayed set (attaches to paw) |
| `mane` *(new)* | neck ridge (lion/horse) |
| `ear` *(new module)* | floppy, pointy, bat, long |
| `tail` | serpent, dragon, fish(+fin), lion-tuft, scorpion |
| `head` | humanoid, draconic, lion, avian(beak), cephalopod |

New slots (`horn`, `tusk`, `claw`, `mane`, `ear`) need a socket on the host
(e.g. `head.horns` ring/pair, `head.tusks`, `paw.claws`, `neck.mane`,
`head.ears`). Adding a socket is data, not machinery.

## 6. What changes vs. reused

**New (additive, the "variant axis"):**
- registry variant tables + `build_module(kind, variant, params)`.
- recipe `variant` field; one grammar rule; capability `variants` list.
- NL variant keyword layer.
- the variant module factories + new slots/sockets (the art budget).

**Reused unchanged:** the v2 socket resolver (`assembly`), `geometry`, `skinning`,
`uv`, `paint`, `texture`, `animate`, determinism, budget back-off, and the whole
`unreal-mcp-rx` handoff. Variants change *which bones/blobs a module emits*,
nothing downstream.

**Backward compatible:** every v2 recipe/template stays valid (variant omitted →
default). The existing single-form modules become the default variant of their
kind.

## 7. Risks & mitigations

- **Combinatorial blow-up.** N kinds × M variants is large. *Mitigation:* curate
  (3–5 variants per slot that creatures actually want); the capability report
  bounds what the LLM can ask for; fail closed on the rest.
- **Capsule fidelity for thin parts** (feathers/membranes). *Mitigation:* accept
  stylized now; track the optional flat-primitive enhancement (§4).
- **Antler/branch topology.** Branching bones can produce awkward SDF joins.
  *Mitigation:* the largest-component + manifold gate already guards it; tune
  smooth-min per part if needed.
- **Animation per variant.** A feathered wing flaps like a bat wing for now (the
  `wing` animator targets the arm). *Mitigation:* per-variant animators are a
  later refinement; the kind-level animator is a fine default.
- **NL ambiguity** ("horn" with no qualifier). *Mitigation:* fall back to the
  kind's default variant + warn.

## 8. Proposed milestones

- **V3-M0 — Variant mechanism.** *(shipped.)* `registry.py` now holds per-kind
  `ModuleKind(default, variants, params)` tables + `build_module(kind, variant,
  params)` + legacy `ALIASES`; `recipe.py` validates the optional `variant`
  (unknown → fail closed; omitted → default) with **variant-specific socket**
  checks; `capability_report` lists `variants`/`defaultVariant`; NL emits `head` +
  variant. Demonstrated by consolidating the three head forms into one `head` kind
  (`humanoid`|`draconic`|`cephalopod`), with `draconic_head`/`cephalopod_head` as
  aliases; `wing` re-expressed as `wing/bat`. **Exit (met):** variants round-trip,
  validate fail-closed (incl. variant-only sockets like `head.face`), v2
  recipes/templates unchanged. 11 new tests (109 total).
- **V3-M1 — Wing variants.** *(shipped.)* `wing` now has four variants —
  **bat** (webbed fingers), **feathered** (a fan of separated quill capsules —
  gapped so smooth-min keeps them distinct), **membrane** (a stiff glider delta),
  **insect** (thin twin lobes) — all stylized capsule-SDF per decision A. NL maps
  feather/swan/angel → feathered, insect/fairy/dragonfly → insect,
  glider/membrane/leathery → membrane. **Exit (met):** each variant builds
  watertight + within budget; feathered and membrane verified live in UE 5.7 and
  read distinctly from bat. 6 new tests (114 total). Stylized chunkiness is on the
  membrane (broad delta reads a touch paddle-y) — accepted as on-style.
- **V3-M2 — Horn variants + the `horn` slot.** *(shipped.)* New `horn` kind with
  five variants — **unicorn** / **rhino** (single) and **antler** (branching
  beam+tines, bilateral) / **ram** (curled) / **bull** (swept) — attached via a
  new `head.horns` socket added to all three head variants. `unicorn` + `stag`
  templates registered; NL maps unicorn/antler/deer/ram/bull/rhino keywords to the
  horn variant (and "horn" no longer mis-triggers a draconic head — horns are
  their own slot). **Exit (met):** unicorn (single horn, verified live in UE) and
  stag (antlers) generate watertight; each horn variant builds. 6 new tests
  (119 total).
- **V3-M3 — Tusks, hooves, claws, manes, ears.** New slots + variants. **Exit:** a
  boar (tusks), a horse (hooves + mane), a feline (claws) generate.
- **V3-M4 — NL variant keywords + presets.** "a deer-antlered, feather-winged
  dragon" composes correctly. **Exit:** variant-aware prompts route end to end.
- **V3-M5 — Variant corpus.** Sample variants per slot; all build valid +
  deterministic; no degenerate joins. **Exit:** corpus green.

## 9. Open questions

1. Variant *params* vs discrete names — is a wing `span`/`droop` continuous, or
   only named variants? (Propose: named variant + a few continuous params.)
2. Should some "variants" actually be separate `kind`s (e.g. `antler` vs `horn`)?
   (Propose: keep one `horn` kind with variants; reduces socket sprawl.)
3. ~~The flat/membrane primitive — worth it?~~ **Resolved: no — stay stylized
   (§4).** Lightweight project; keep one unified SDF mesh.
4. Per-variant animation — when does a feathered wing need its own flap?
5. Texture per part/variant — feathers vs scales vs fur as a `skin` hint per
   module (ties back to v2's `--free` per-module skin)?

## 10. Scope guardrail

"Variance, but curated." Ship **3–5 variants** for the slots creatures actually
use, and the handful of new anatomical slots (horn, tusk, claw, mane, ear).
Resist an unbounded part editor. Novelty comes from *choosing among curated
variants* — the same bounded-novelty philosophy as v1 and v2, one level deeper.
