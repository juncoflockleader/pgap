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
  ring already cover bilateral, radial, and chained bodies).

## Milestones

- **L0 — Authoring guide + checklist.** **Exit:** a contributor can add a part end
  to end following the doc; the corpus gates it.
- **L1 — Body bases.** serpentine, hexapod, arachnid, avian, centaur. **Exit:**
  each builds a valid creature; a snake, a spider, a bird generate.
- **L2 — Slots batch.** beak, frill, spikes, shell, gills, whiskers, mandibles,
  dorsal fin, stinger. **Exit:** each module builds + composes on a host.
- **L3 — Presets batch.** griffin, manticore, wyvern, pegasus, hydra, naga,
  phoenix, basilisk, chimera, centaur. **Exit:** all generate + read as described;
  NL routes their names.
- **L4 — Bestiary catalog.** generator + gallery doc with thumbnails. **Exit:**
  the gallery renders every template.
- **L5 — Corpus sweep.** all new bases/slots/variants/presets in the corpus;
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
