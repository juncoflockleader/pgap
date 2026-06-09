# Roadmap 3 — v4: Faces

Status: **Implemented (lightweight, geometry path).** Appearance (F0) is met by the
roadmap-2 **geometry** face — eyes (+ iris), nose, mouth, beak/mandibles — rather
than a face texture (a deliberate deviation: the geometry faces already read well
in the bestiary, so the trickiest piece, face-UV, was not needed). The new V4 work
is the **expression rig**: a `maw` head variant with a hinged `jaw`, pupilled eyes,
and `mouth_open` / `eye_look` clips. F1–F4 done; the clips import as valid playable
AnimSequences on the wolf skeleton in UE 5.7.4 (0 issues), and the jaw-open / pupil
deformation is verified numerically (`test_faces`).

## Motivation

Faces are the natural next expressive axis: eyes, a mouth, markings, and a bit of
expression (mouth open to bark/roar, eyes that look). Done right it makes
creatures feel *alive*. Done wrong it drags pgap toward photoreal facial rigs and
abandons what makes it simple. This roadmap is the **lightweight** path.

## The split — and the trap

Faces are two separable things:

1. **Appearance** (eyes / mouth / nose / markings) → **texture** on a face region
   of the head. Cheap, on-brand, no geometry machinery.
2. **Expression** (mouth open, eyes look, blink) → either **bones** or **morph
   targets**.

**The trap — avoid morph targets.** Blendshapes need stable vertex correspondence
across shapes; marching cubes gives *different topology per SDF*, so morphs
fundamentally fight the kernel. Chasing morph-based facial animation would mean
abandoning the thing that keeps pgap simple.

**The pgap-native answer — a few face bones.** A `jaw` bone (opens a mouth that is
*geometry*), `eye_l`/`eye_r` bones (rotate the eye spheres we already make for the
beholder), optional `brow_l`/`brow_r`. Expression then animates exactly like
everything else — joint-rotation clips. Skeleton-first, deterministic, lightweight.

## The idea

- **Face textures:** a known **face UV region** on the head, painted with eyes, a
  mouth line, a nose, and markings (palette/keyword-driven, like coats). Static
  but immediately expressive.
- **Face rig:** a head variant (or a `face` module) carrying a `jaw` + `eye_l/r`
  (+ brows). The mouth and eyes are small geometry blobs the bones drive.
- **Expression clips:** `mouth_open` (bark/roar — jaw rotates), `eye_look` (eyes
  rotate), and "blink" approximated by an eye/lid texture state if cheap (else
  skipped). Composed by the modular-animation system (V2-M3) like any clip.

## What's reused vs new

**Reused:** skeleton-first (face bones are just bones); the **eye sphere** module
already exists; modular animation (jaw/eye rotation clips); `texture.py` +
`paint.py` (face-region paint); the assembler.

**New (moderate):**
- a **head face-UV region** (consistent projection so features paint to a known
  spot) — UV work on the head, the trickiest piece.
- a **face texture generator** (eyes, mouth, nose, markings).
- a **face rig**: jaw + eye bones, and a head variant with a *mouth/jaw* geometry
  the jaw bone deforms; bind eye spheres to the eye bones.
- **expression clips** (mouth_open, eye_look).

## Milestones

- **F0 — Face appearance.** ✅ **done via geometry (roadmap 2)** — eyes (+ iris),
  nose, mouth line, beak/mandibles read as a face in the bestiary; the planned
  *texture* face-region was unnecessary (kept it geometry, on-brand). **Exit:** ✔
- **F1 — Face rig.** ✅ **done** — a `maw` head variant (skull + snout + a hinged
  `jaw` bone) and pupilled eyes (`eyes_module` gains a `pupil` riding each sclera).
  Rest pose is identity; weights valid. **Exit:** the face rig skins cleanly. ✔
- **F2 — Expression clips.** ✅ **done** — the clip-aware modular animator emits
  `mouth_open` (the jaw rotates open/closed — bark/roar) and `eye_look` (the eyes
  rotate, pupils swing — gaze). `test_faces` verifies the jaw drops + the pupil
  swings by posing the skinned mesh. **Exit:** a creature barks (jaw opens) in UE —
  the `wolf`'s `mouth_open`/`eye_look`/`idle` import as valid playable AnimSequences
  on its skeleton in UE 5.7.4 (0 issues). (A posed in-engine screenshot is blocked
  by the bridge's instance-edit guard; the jaw-open deformation is proven in tests.)
- **F3 — Face variants + NL.** ✅ **done** — eye variants (round/almond/slit) +
  size + iris color; the `maw` head; NL routes "a wolf"/"snarling beast" → maw, and
  "an angry big-eyed beast" → big eyes. **Exit:** variant-aware faces. ✔
- **F4 — Face corpus.** ✅ **done** — the `maw` variant + `wolf` template are
  corpus-gated (valid + deterministic); `test_faces` checks the rig deforms.
  **Exit:** green. ✔

## Risks & decisions (be honest)

- **Capsule blobs are the hardest place for a readable face.** A smooth head has
  no natural mouth/eye sockets. *Decision:* lean on **texture** for appearance;
  use minimal geometry (eye spheres + a small jaw blob) only where bones must
  deform it. If it looks uncanny, prefer painted faces over geometric ones.
- **Face-UV consistency.** Heads point different ways (humanoid up, draconic
  forward). *Decision:* per-head-variant face projection, defined with the head.
- **Jaw needs mouth geometry to open.** *Decision:* a dedicated face-bearing head
  variant that includes a lower-jaw blob; plain heads stay faceless.
- **Scope creep toward real facial animation.** *Decision:* hard stop at
  jaw + eyes (+ brows). No lids/cheeks/muscles, no morphs.

## Out of scope (firmly)

Morph targets / blendshapes, FACS-style rigs, lip-sync, wrinkle maps, hair.
