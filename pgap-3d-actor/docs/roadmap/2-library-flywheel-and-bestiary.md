# Roadmap 2 — Library flywheel + bestiary

Status: Planned (after surface treatments). Growth by breadth.

## Motivation

Once creatures *look* good (roadmap 1), the next lever is **breadth** — more body
plans, more parts, more named creatures. The architecture makes each addition a
small, isolated, testable module (data, not machinery). The goal of this roadmap
is twofold: **widen the library**, and make widening it **sustainable and
browsable** — so it can scale (even community-contributed) without becoming
complex.

## Two halves

### A. The flywheel (make growth cheap + safe)

- **Module-authoring guide** — a short, concrete "how to add a kind / variant /
  template" doc + a checklist (author the module, give it sockets, register it,
  add a corpus entry, add NL keywords).
- **The corpus is the gate.** `test_v3_corpus` already builds every kind/variant/
  template; any new part must pass it (valid, watertight, within budget,
  deterministic). That's the entire contribution contract — a new part is a tiny,
  reviewable PR that can't break the rest.

### B. The content batch (the first big expansion)

#### B0 — Flagship first part: **eyes** (the most important organ) — ✅ done (dog)

Status: **implemented for the dog (v1) and generalized to every v2 head** — two
non-fused, dark, proud "bead" eyes (E0/E1), plus a **black nose, lower jaw, and
mouth line** ("jaws"). Built on two reusable kernel capabilities, now on **both**
the part path and the bone path: `fused=False` (a non-fused organ that sits proud
instead of melting into the smooth-min body) and `region` (color an organ
independently of its bone). The v2 assembler threads both flags from `BoneSpec`
→ `Bone` → the SDF kernel, so the modular `eyes` module is a mirrored pair of
proud, region-tagged eyeball bones at a head's `eyes` socket. **Variants:** round /
almond / slit (E1). **Done (E2):** every head variant (humanoid / draconic /
cephalopod) and the arachnid carry an `eyes` socket; all head-bearing presets ship
eyes; the beholder/kraken eye organs are region-tagged too; NL routes shape + size
("slit-pupil eyes", "big eyes"); **iris color** via `material.eyeColor` (amber /
green / glowing-red …, NL-routed from "amber eyes" / "red-eyed"); the corpus +
`test_v2_eyes` gate it. Remaining: the expressive eye-bone rig (roadmap 3). v1
live-verified in UE 5.7.4.

**Static jaws — ✅ generalized to v2 too.** The dog's nose + mouth line now ride
the same bone path as eyes: a `jaws` module (a proud non-fused **nose** bead,
region `nose`, above a *fused*, region-`mouth` lip line that tints without
bulging) at a per-head `jaws` socket. Every head variant has the socket; every
head-bearing preset ships jaws (draconic snouts get a tip nose; the avian uses the
`lipped` no-nose variant for a beak); NL routes `beaked`/`no nose` → lipped;
`test_v2_jaws` gates it. The *openable* jaw **bone** (bark/roar) stays roadmap 3.

Eyes lead the batch. They're the highest-value addition — eyes are what make a head
read as a *face*, and **creatures today have none** (the dog has a snout, cheeks,
and a nose blob, but no eyes). Geometrically an eye is trivial — a sphere at a head
socket, structurally identical to a horn — which makes it the ideal first concrete
part. But it forces three decisions that set the convention for *every* future
organ (teeth, claws, gems, beaks):

1. **Non-fusion.** The kernel smooth-mins everything into one watertight blob, which
   would swallow a small eyeball. Eyes must be a **non-fused element** that sits
   *proud* of the head surface — the first part that is *not* blended into the body.
   This "separate blob / second mesh element" concept is reused by teeth, claws,
   inset gems, etc. *Decision:* add a non-fused part flag to the kernel.
2. **The eye material.** An eye wants glossy sclera + a colored iris + a dark pupil
   (+ a catchlight) — distinct from fur/skin. *Decision:* paint the iris/pupil onto
   the eyeball's own UVs via the existing base-color texture (texture-side,
   on-brand); promote to a second glossier material slot only if needed.
3. **Painted eyes vs. geometry eyes.** The cheapest first cut is a **decal** — paint
   the eyes straight onto the head texture (ties into roadmap 1's texture layer):
   flat, but reads fine at stylized distance and is zero geometry risk. Geometry
   eyeballs (catchlights, correct from side angles) are the upgrade. *Decision:*
   ship painted-on eyes first, then geometry eyeballs as a variant.

The module machinery already exists (`eyeball_module`, `eyestalk_module` from the
beholder/kraken) — it just isn't wired onto standard heads. Give every head an
`eyes` socket (mirrored pair; `ring` for radial/extra eyes, as the beholder does).
**Variants:** round, almond, slit-pupil (reptile), compound (insect), googly.
**Params:** size, spacing, iris color, pupil shape.

*Static, placed eyes belong here; the expressive **eye-bone** rig (blink, gaze,
emotion) is roadmap 3 — a creature should* have *eyes long before it can emote.*

#### B1 — Bases, slots, variants, presets (the breadth batch)

- **Body bases:** `serpentine` (no legs), `hexapod`/insect thorax (6 legs),
  `arachnid` (radial 8-leg), `avian` (bird torso), `centaur` (quadruped body + a
  humanoid-torso socket). Each is one new root module with sockets.
- **Slots:** beak, frill, spikes/spines, shell/carapace, gills, whiskers,
  mandibles/pincers, dorsal fin, crest, stinger, pouch.
- **Variants:** more heads (avian/feline/equine/reptilian/skull), tails
  (scorpion/club/plume), legs (digitigrade/insectoid).
- **Named presets:** griffin, manticore, wyvern, pegasus, **hydra** (multiple
  neck+head attachments — already expressible), naga, phoenix, basilisk, chimera,
  centaur. Each ~10 lines.

### C. The bestiary catalog (browsable output)

- A **catalog generator** that renders every template (and a sample of variants)
  to a thumbnail and writes a **gallery markdown** — so a user/agent can *see*
  what exists. Reuse the existing thumbnail mechanism (UE bridge today; a headless
  glTF renderer is a nice-to-have later).

## What's reused vs new

**Reused:** the entire pipeline — every base/slot/variant/preset is data through
the unchanged kernel. The corpus test pattern. The NL inference layer (add
keywords). The thumbnail mechanism.

**New (minimal):**
- the authoring guide (docs).
- the catalog generator (a script: build each template → render thumbnail → emit
  a gallery md).
- one resolver feature *if* a new base needs it (most won't — sockets + mirror +
  ring already cover bilateral, radial, and chained bodies). **Added:** optional
  per-attachment `rotation` (yaw/pitch/roll degrees) that pivots a module about its
  socket — a byte-exact no-op at zero, Z-symmetric under mirror, validated in the
  recipe grammar. Enables fanned necks (hydra), swept/angled limbs, tilted parts.

## Milestones

- **L0 — Authoring guide + checklist.** **Exit:** a contributor can add a part end
  to end following the doc; the corpus gates it.
- **L1 — Eyes (flagship organ, do first).** The lead concrete part (see B0):
  - *E0 — Painted eyes.* An `eyes` decal in the head base-color (iris + pupil +
    catchlight) at a head-socket position. **Exit:** the **dog has visible eyes**;
    deterministic.
  - *E1 — Geometry eyeballs.* ✅ **done** — a **non-fused** eyeball at the `eyes`
    socket; variants round / almond / slit. Eyes are bone-borne organs (non-fused
    + region now work on bones, not just parts), so they don't melt into the head.
  - *E2 — Eyes everywhere.* ✅ **done** — every head variant (+ the arachnid) has
    an `eyes` socket; every head-bearing preset ships a pair; NL routes shape +
    size ("slit-pupil eyes", "big eyes"); corpus + `test_v2_eyes` green. Remaining:
    the expressive eye-*bone* rig → roadmap 3 (iris color now ships via
    `material.eyeColor`).
- **L2 — Body bases.** ✅ **done** — serpentine, hexapod, arachnid, avian, centaur.
  `serpent` (legless cobra-ish chain), `avian` (torso + 2 legs + feathered wings +
  tail), `arachnid` (cephalothorax + abdomen + 8 splayed `spider_leg`s on a ring),
  `hexapod` (abdomen/thorax/head + 3 bilateral `insect_leg` pairs + eyes/jaws on the
  head; optional wings socket), and `centaur` (the horizontal `body` with the
  vertical biped `spine` plugged into its neck — a humanoid torso + arms over four
  legs, no new module). All implemented, NL-routed, and corpus-gated; serpent/avian/
  arachnid live-verified in UE 5.7.4. **Exit:** each builds a valid creature; a
  snake, a spider, a bird, a bug, a centaur generate.
- **L3 — Slots batch.** beak, frill, spikes, shell, gills, whiskers, mandibles,
  dorsal fin, stinger. **Exit:** each module builds + composes on a host.
- **L4 — Presets batch.** ✅ **done** — griffin, manticore, wyvern, pegasus, hydra,
  naga, phoenix, basilisk, chimera (centaur shipped in L2). Each is a ~10-line
  recipe over existing bases + parts: griffin (lion body + feathered wings + beak +
  talons), manticore (lion + mane + bat wings + spiked tail), wyvern (two-legged
  winged dragon), pegasus (winged hooved horse), hydra (three tall necks + draconic
  heads on a `hydra_body`), naga (humanoid torso + serpent tail), phoenix (crested
  bird + plume), basilisk (crowned serpent), chimera (maned lion + ram horns +
  serpent tail). All registered, NL-routed (word-boundary matched so `manticore`/
  `wyvern` no longer collide with sphinx/dragon), corpus-gated, and in the bestiary
  gallery; `test_presets` checks structure (wyvern 2 legs, hydra 3 heads, naga/
  basilisk legless). **Exit:** all generate + read as described; NL routes their
  names. The hydra's three heads **fan out** via per-attachment rotation (below).
- **L5 — Bestiary catalog.** ✅ **done** — `pgap.catalog` builds every template and
  renders a deterministic thumbnail with a new **headless software renderer**
  (`pgap.render` — pure-numpy z-buffer rasterizer, shades the mesh's own vertex
  colors so coats + eyes/iris/nose/mouth show; *no engine needed*, unlike the
  parking-lot UE path). Writes `docs/BESTIARY.md` + `docs/bestiary/*.png`; run via
  `python -m pgap.catalog` or `--catalog`. The gallery doubles as an at-a-glance
  visual regression. `test_catalog` gates it. **Exit:** the gallery renders every
  template. ✔
- **L6 — Corpus sweep.** all new bases/slots/variants/presets in the corpus;
  sample variants to keep runtime bounded. **Exit:** green.

## Risks & decisions

- **Combinatorial sprawl.** *Decision:* curate (3–5 variants per slot that
  creatures actually use); the capability report bounds what the LLM can request.
- **Socket consistency across bases.** A `wings`/`neck`/`tail` socket should mean
  the same thing on every body. *Decision:* a small socket-naming convention in
  the authoring guide.
- **Corpus runtime as it grows.** *Decision:* sample (one representative variant
  per slot in the full-cross test; exhaustive isolation test stays per-module).
- **Catalog rendering needs the UE bridge.** *Decision:* fine for now; a headless
  glTF thumbnail renderer is a parking-lot nice-to-have.

## Out of scope

Open-vocabulary geometry; anything needing a new geometry path.
