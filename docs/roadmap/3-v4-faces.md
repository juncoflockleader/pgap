# Roadmap 3 — v4: Faces

Status: Planned (after surfaces + library). Highest value, **highest
uncertainty** — do it last, keep it lightweight.

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

- **F0 — Face UV + basic face texture.** A face region on the head; paint eyes +
  a mouth. **Exit:** a head reads as having a face in a viewer.
- **F1 — Face rig.** A head/face variant with `jaw` + `eye_l/r` driving mouth +
  eye geometry; weights valid; rest pose identity. **Exit:** the face rig skins
  cleanly.
- **F2 — Expression clips.** `mouth_open`, `eye_look` via the modular animator.
  **Exit:** a creature barks (jaw opens) in UE.
- **F3 — Face variants + NL.** face/eye/mouth variants (big eyes, fanged, beaked,
  expressionless); "an angry big-eyed beast" routes. **Exit:** variant-aware faces.
- **F4 — Face corpus.** every face variant builds valid + deterministic; rig
  weights valid. **Exit:** green.

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
