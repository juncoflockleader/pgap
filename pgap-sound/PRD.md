# PRD: pgap-sound — Procedural Sound Asset Pipeline (psap)

Status: Draft v1 (planning).
Part of the `pgap` monorepo. Sibling of `pgap-3d-actor`; shares its architecture,
determinism guarantees, and `unreal-mcp-rx` handoff.

---

## 1. Summary

Build a **deterministic, dependency-light, offline** generator that turns a spec
(e.g. `"a laser zap"`, `"a wooden thunk"`, `"a low crackling fire loop"`, `"a
small dragon growl"`) into a **game-ready sound** — synthesized from DSP, exported
as WAV — rather than recorded or produced by a text-to-audio model.

This is "Architecture B" for audio, the direct analog of `pgap-3d-actor`: own the
whole stack so output is reproducible, free, and consistent in style. The
deliberate trade is **synthesized, not recorded** (stylized, not foley-realistic)
— exactly as the 3D side trades stylized for photoreal.

It is a *better* fit than 3D in two ways: procedural audio (DSP synthesis) is a
mature, decades-old field, and the pipeline is **shorter** — audio is a 1-D sample
stream, so there is no rigging/skinning/UV analog.

## 2. Problem & motivation

A creature, weapon, or UI needs sound. Recorded foley is expensive and licensing-
bound; text-to-audio models are non-deterministic, online, and overkill for game
SFX. Yet **most game sounds are eminently synthesizable** — the beloved
`sfxr`/`bfxr` generators have made retro SFX from ~10 parameters for 15 years.
This PRD generalizes that idea (modular, NL-driven, more categories) into a
deterministic pipeline that *completes the creature* `pgap-3d-actor` already makes
(the dog's bark, the dragon's roar) and stands alone for any game audio need.

## 3. Goals / non-goals

### Goals
- Synthesize **game-ready sounds** from a structured spec, exported as WAV (+
  manifest) that the existing `unreal-mcp-rx` bridge imports as a `SoundWave`.
- **Deterministic:** same spec + seed → byte-identical samples. No network in the
  core path.
- **Category-routed:** a cheap path for one-shot SFX, a modal path for impacts, a
  noise/loop path for ambience, a vocal path for stylized creature sounds.
- **Parametric & composable:** synthesis modules (oscillator, envelope, filter,
  noise, modal bank, effects) wired by a recipe, with named variants — driven by
  named parameters an LLM (or human) can fill.
- **Fail-closed** capability report + validation, mirroring the 3D side.
- Plug into the `unreal-mcp-rx` audio asset role with no changes to the bridge.

### Non-goals (v1)
- **Speech / dialogue / lyrics** — needs TTS (a model). Out of scope (the audio
  equivalent of open-vocabulary geometry). Route to a model if ever needed.
- **Music** — full songs, genre-faithful production, melodies as a deliverable.
  Out of scope (the Suno/Udio domain). *Short non-melodic UI stingers* are a grey
  area, deferred. **"Mainly sound," not music, not voice.**
- **Recorded/foley realism** — the "photoreal" of audio. Synthesis approximates;
  fidelity is bounded by design.
- **Runtime DSP engine integration** — bake WAVs offline in v1; in-engine
  procedural audio is a later possibility, not a v1 goal.

## 4. Users & use cases
- **The MCP agent:** fills the audio role of a source-worker handoff (the bark
  sound for `pgap-3d-actor`'s golden retriever; the laser for a weapon).
- **A developer:** `python pgap.py sound --spec laser.json` (or `--describe "a
  retro coin pickup"`) to produce a WAV directly.
- **The LLM front-end:** converts a natural-language request into the structured
  sound spec, then invokes generation.

## 5. Key insight: synthesis, not recording

The two hardest 3D stages (rig/skin) have **no audio analog**, so the pipeline is
short: **a graph of DSP modules rendered into a sample buffer.** Every category of
target is a known synthesis technique:

- **One-shot SFX** = pitched oscillator(s) + a fast envelope + optional sweep,
  noise, and effects (the `sfxr` model).
- **Impacts** = **modal synthesis** — a bank of decaying resonant sine modes whose
  frequencies/decays encode the material (wood / metal / glass / stone), excited by
  an impulse.
- **Ambience/loops** = filtered/granular **noise** shaped by slow envelopes (wind,
  rain, fire, water, hum, drones), rendered seamlessly loopable.
- **Stylized creature vocals** = FM / formant synthesis + a pitch contour + noise
  (growl, chirp, roar, squeak) — the *direct analog of the stylized creatures*
  `pgap-3d-actor` makes.

The "knowledge" is **synthesis recipes + small parameter tables** — kilobytes —
not a trained model. WAV is written directly (a documented format), like glTF.

## 6. System architecture

```
spec / prompt ─▶ validate (fail-closed) ─▶ [ one seeded PCG64 RNG ]
   │                                              │
   ▼                                              ▼
 CATEGORY ROUTER  (sfx | impact | ambient | vocal | ui)
   │
   ▼
 SYNTH GRAPH  — modules wired by the recipe:
   sources:   oscillator (sine/square/saw/tri/noise), modal bank, sample-less
   shaping:   ADSR / decay envelopes, pitch/freq contour, filters (lp/hp/bp biquad)
   texture:   noise mix, granular, FM/formant
   effects:   distortion, bitcrush, delay, reverb, chorus
   │
   ▼
 RENDER  → float sample buffer → normalize / soft-limit (no clipping) → loop-seam
   │
   ▼
 ASSEMBLE  → <Name>.wav (PCM16) + manifest.json (spec hash, seed, SHA, license)
```

Mirrors `pgap-3d-actor`: pure-function stages, one RNG, I/O at the edges, a
module/recipe model with named variants, a capability report, and a CLI.

## 7. Inputs & outputs

### Input: sound spec (JSON)
```jsonc
{
  "name": "LaserZap",
  "category": "sfx",                 // sfx | impact | ambient | vocal | ui
  "seed": 12345,
  "durationMs": 350,
  "sampleRate": 44100,
  "graph": {                          // category-specific synth params (validated)
    "osc": { "wave": "square", "freq": 1200, "sweep": -800 },
    "env": { "attack": 1, "decay": 320 },
    "filter": { "type": "lowpass", "cutoff": 4000, "resonance": 0.3 },
    "fx": ["bitcrush"]
  },
  "gain": -3.0                        // target peak dBFS (loudness-normalized)
}
```
Recipes (category presets) and a `--describe` NL front-end author this, exactly
like the 3D side's `--creature` / `--describe`.

### Output
- `<Name>.wav` — PCM16 mono (or stereo for ambience), loopable when `category` is
  ambient.
- `manifest.json` — spec hash, seed, generator version, per-file SHA-1, license
  ("procedurally generated original work").
- (with `--handoff`) the role-named bundle the `unreal-mcp-rx` audio role consumes.

## 8. Functional requirements
- **FR1 Deterministic** — identical (spec, seed) → identical WAV bytes; no network
  in the core (seed the noise RNG; fixed sample dtype/format).
- **FR2 Clean import** — WAV imports via `unreal-mcp-rx` as a `SoundWave` with no
  errors; valid header, no clipping, correct sample rate.
- **FR3 Loopable ambience** — `ambient` outputs are seamlessly loopable
  (crossfaded/zero-crossing aligned).
- **FR4 Loudness-safe** — peak-normalized to a target dBFS with a soft limiter; no
  hard clipping; consistent perceived loudness across a batch.
- **FR5 Fail-closed** — unsupported category / unknown module / out-of-range param
  → validation error, not a guess. A capability report enumerates support.
- **FR6 Handoff** — slots into the `unreal-mcp-rx` audio asset role; the golden
  retriever's bark is generated, not placeholdered.

## 9. Quality bar & acceptance
- **Recognizability:** a neutral listener labels the output as the requested sound
  ("a laser", "a wood hit", "fire") in a blind check.
- **Import:** zero import errors; a `SoundWave` is created and audible in PIE.
- **Reference case:** generate the **bark** for `pgap-3d-actor`'s golden retriever
  and the **roar** for a dragon; both import and drive the existing bark/behavior
  proof — replacing the placeholder WAV used today.
- **Determinism:** a fixture spec re-run diffs to an identical WAV SHA.
- **Variance:** N seeds of one spec all read as the same sound (no degenerate /
  silent / clipped output) — a golden corpus.

## 10. Milestones (phased)

- **M0 — SFX core & determinism.** The `sfxr`-style one-shot path: oscillator +
  sweep + ADSR + filter + noise mix, render → PCM16 WAV, seeded RNG, WAV writer,
  determinism test. **Exit:** a laser/coin/jump that imports and clearly beats
  silence.
- **M1 — Impacts (modal synthesis).** A resonant-mode bank with material presets
  (wood / metal / glass / stone), impulse excitation. **Exit:** distinct material
  hits.
- **M2 — Ambient loops.** Filtered/granular noise + slow envelopes, seamless
  looping (FR3). **Exit:** wind / fire / rain / hum loops that don't click.
- **M3 — Creature vocals.** FM/formant + pitch contour + noise; growl / chirp /
  roar / squeak. **Exit:** a stylized bark + a dragon roar.
- **M4 — Recipe grammar + NL front-end.** Category presets, fail-closed validation,
  capability report, `--describe` keyword inference. **Exit:** "a retro coin
  pickup" / "a metal clang" route end to end.
- **M5 — Proof integration.** Wire into the `unreal-mcp-rx` audio role + the
  golden-retriever bark/behavior proof; generate the bark/roar that replace the
  placeholder. **Exit:** FR6.

## 11. Determinism, provenance, licensing
- One `Generator(PCG64(seed))` threaded through every stage; no wall-clock; fixed
  sample format. CI re-runs a fixture spec and diffs the WAV SHA.
- Each output carries a manifest (spec hash, seed, version, per-file SHA-1, and a
  "procedurally generated original work" license note) — no third-party rights.

## 12. Risks & mitigations
- **"Sounds cheap."** Humans are sensitive to synthetic audio; tolerance is lower
  than for a stylized mesh. *Mitigation:* invest in the synthesis recipe library +
  light FX (subtle reverb/saturation) + loudness/EQ polish; set expectations
  (stylized); keep a model path (path A) available for hero audio.
- **Music/voice demand off-table.** A real slice of "game audio" needs models.
  *Mitigation:* scope tightly to SFX/impact/ambient/vocal from day one; route
  music/voice elsewhere.
- **Loudness/mix consistency.** *Mitigation:* peak/RMS normalization + a soft
  limiter as an FR4 gate (deterministic DSP).
- **Loop seams.** *Mitigation:* zero-crossing alignment + short crossfade; an FR3
  gate that checks endpoint continuity.
- **Recipe authoring is an art** (like the 3D part library). *Mitigation:* start
  from `sfxr`'s proven model + Andy Farnell's *Designing Sound* patches, ported to
  numpy; grow the library as a contributable, corpus-gated set.

## 13. Dependencies & constraints
- Core: pure Python + numpy. WAV written by hand (PCM16 header + samples). Optional
  `scipy.signal` for filters, or hand-rolled biquads to stay zero-dep. **WAV only**
  in v1 (uncompressed, deterministic, like the hand-written glTF); an OGG encoder
  is an optional, isolated dependency later.
- No ML framework, no audio engine, no network in the core path.
- Reuses, unchanged: the `unreal-mcp-rx` audio asset role + import; the
  source-handoff manifest contract.

## 14. Open questions
- Module/recipe model: how closely to mirror `pgap-3d-actor`'s socket graph vs a
  flatter "synth chain" (audio graphs are mostly linear chains + a few parallel
  buses)?
- Modal data: hand-tune material mode banks, or derive from simple shape/material
  params?
- Stereo/spatialization: mono assets + engine spatialization (recommended), or
  generate stereo ambience?
- Package name: `psap` (proposed) under `pgap-sound/`, run via `python pgap.py
  sound …`.
- Sample rate / bit depth defaults (44.1 kHz / PCM16 proposed).

## 15. Relationship to pgap-3d-actor & unreal-mcp-rx
`pgap-3d-actor` makes the dog; `pgap-sound` makes the bark — and the M5
source-handoff bundle on the 3D side already has the `S_<Name>_Bark.wav` audio
slot (currently a placeholder). Together they realize a creature from one prompt.
`unreal-mcp-rx` provides the audio last mile (import as `SoundWave`, assign to the
bark behavior, PIE-prove) — built and reused unchanged.
