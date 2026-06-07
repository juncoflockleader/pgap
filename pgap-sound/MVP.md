# pgap-sound (psap) — MVP milestones

Concrete, phased plan to a usable first version. Companion to [PRD.md](PRD.md)
(the PRD says *what/why*; this says *what to build first, in what order, and when
it's done*). Mirrors the milestone style of `pgap-3d-actor/docs/milestones/`.

---

## What the MVP is

> Describe a sound, get a deterministic, game-ready WAV that imports into Unreal —
> including the **bark/roar that voices a `pgap-3d-actor` creature**.

The MVP proves the thesis (synthesize, don't record), is usable end to end via the
wrapper (`python pgap.py sound …`), and visibly completes a creature: the golden
retriever's bark, generated rather than placeholdered.

### In scope (MVP)
- **One-shot SFX** (the `sfxr` model): lasers, coins, jumps, pickups, UI blips,
  hits, powerups.
- **Stylized creature vocals**: bark, growl, chirp, roar, squeak.
- Deterministic **PCM16 WAV** output + provenance manifest.
- **Spec + fail-closed validation + capability report + CLI** (wired into the
  wrapper) + a small **NL front-end** (`--describe`).
- **Loudness-safe** render (peak-normalize + soft limiter; no clipping).
- **Unreal handoff**: imports as a `SoundWave`; generates the dog's bark for the
  existing bark/behavior proof.

### Out of scope (MVP — see Fast-follow)
- Impacts via **modal synthesis** (material hits) — high value, slightly more
  machinery; first fast-follow.
- **Ambient loops** (wind/fire/rain; seamless looping).
- A full **recipe grammar + variants** (MVP uses flat per-category specs).
- **OGG/compressed** output, **stereo**, runtime DSP.
- Music, speech/voice (permanent non-goals per PRD §3).

## Proposed package layout (scaffold at S0, not before)

```
pgap-sound/
  psap/
    __init__.py
    rng.py           # seeded Generator(PCG64) — the determinism spine
    dsp.py           # oscillators, ADSR/decay envelopes, biquad filters, noise
    synth.py         # render a param block -> float sample buffer
    sfx.py           # sfxr-style one-shot params -> synth
    vocal.py         # FM/formant + pitch contour -> creature vocals
    render.py        # normalize + soft-limit + (loop-seam later)
    wav.py           # hand-written PCM16 WAV writer
    spec.py          # Spec dataclass + validation
    capabilities.py  # capability report + validate_spec (fail-closed)
    nl.py            # prompt -> spec
    assemble.py      # write <Name>.wav + manifest.json (+ --handoff)
    cli.py           # `python -m psap.cli` (run via `python pgap.py sound`)
  tests/             # determinism, WAV validity, loudness, category corpus
  fixtures/          # golden specs (laser, coin, bark, roar)
  PRD.md  README.md  MVP.md
```

Pure Python + numpy; WAV written by hand (44-byte header + PCM). Optional
`scipy.signal` for filters, or hand-rolled biquads to stay zero-dep.

## Milestones

**Status — all implemented (23 tests green):** S0 ✅ · S1 ✅ · S2 ✅ · S3 ✅ ·
S4 ✅ · S5 ✅ code + bundle (the *live* UE import is environment-gated on the
editor being open, identical to the 3D M5 capstone; the bark WAV is OS-verified
PCM16 and the import is the same `editor_asset_import` call already proven for the
dog).

### S0 — SFX core + determinism + WAV  *(the heart)* ✅
- `rng.py`, `dsp.py` (sine/square/saw/tri/noise oscillators; ADSR + exp-decay
  envelopes; one biquad lowpass; freq sweep), `synth.py`, `sfx.py`, `wav.py`,
  `assemble.py`, a minimal `spec.py`, `cli.py`.
- One seeded RNG threaded through (noise is the only stochastic source).
- **Exit:** `python pgap.py sound --spec laser.json` writes a `LaserZap.wav` that
  is audibly a laser and clearly beats silence; re-run → **identical SHA**.
- **Tests:** `test_determinism` (same spec+seed → identical WAV bytes),
  `test_wav_valid` (correct RIFF header, sample rate, length, no NaN).

### S1 — Render polish (loudness + limiter)  *(FR4)* ✅
- `render.py`: peak-normalize to a target dBFS; soft limiter; DC-offset removal;
  short fade-in/out to avoid clicks.
- **Exit:** outputs hit the target peak with **no hard clipping**; consistent
  perceived loudness across a batch.
- **Tests:** `test_no_clipping` (|sample| < 1.0), `test_peak_normalized`.

### S2 — Spec + validation + capability report + wrapper wiring ✅
- `spec.py` (per-category param schema), `capabilities.py`
  (`capability_report()` + fail-closed `validate_spec`), CLI flags
  (`--spec`, `--out`, `--capabilities`, `--seed`).
- Mark the `sound` pipeline **ready** in the top-level `pgap.py` wrapper.
- **Exit:** `python pgap.py sound --capabilities` prints the contract; an
  unsupported category/param **fails closed** (error, not a guess).
- **Tests:** `test_capabilities`, `test_validation_fail_closed`.

### S3 — Creature vocals  *(completes the creature)* ✅
- `vocal.py`: FM/formant synthesis + a pitch contour + a noise/growl layer;
  category presets bark / growl / chirp / roar / squeak.
- **Exit:** a stylized **bark** and a **dragon roar** that read as such; sized to
  loop/one-shot as appropriate.
- **Tests:** `test_vocal_builds`, vocals in the determinism corpus.

### S4 — NL front-end  *(`--describe`)* ✅
- `nl.py`: deterministic keyword inference (laser/zap → swept square + fast decay;
  coin/pickup → arpeggiated blips; bark/growl/roar → vocal preset; "retro/8-bit" →
  bitcrush; size/pitch words → freq). Validated; fails closed on unrecognized.
- **Exit:** `python pgap.py sound --describe "a retro coin pickup"` and
  `--describe "a small dragon growl"` route end to end.
- **Tests:** `test_nl` (representative prompts → expected category/params;
  unrecognized → ok=False).

### S5 — Unreal handoff + proof  *(MVP done = FR6)* ✅
- `assemble.py` `--handoff`: emit the audio-role bundle (`S_<Name>_Bark.wav` +
  manifest) the `unreal-mcp-rx` source-handoff contract expects.
- Generate the **golden retriever's bark**; import as a `SoundWave`; feed the
  existing bark/behavior proof (replacing today's placeholder WAV).
- **Exit (MVP):** the bark imports cleanly and drives the bark proof; a
  prompt → playable, *audible* creature.
- **Tests:** `test_handoff` (bundle layout + manifest + sha), import verified live
  via the bridge.

## Definition of done (MVP)

- `python pgap.py sound --describe "<prompt>"` produces a deterministic WAV for
  one-shot SFX and creature vocals, loudness-safe, fail-closed on the unsupported.
- The output imports into UE 5.7 as a `SoundWave`; the dog's bark is generated, not
  placeholdered.
- A test suite covers determinism, WAV validity, loudness, validation, and a small
  category corpus.

## Fast-follow (post-MVP, in order)

1. **Impacts (modal synthesis)** — resonant-mode banks per material (wood / metal /
   glass / stone); the biggest SFX category after one-shots.
2. **Ambient loops** — filtered/granular noise + slow envelopes; **seamless
   looping** (zero-crossing + crossfade; FR3).
3. **Recipe grammar + variants + effects** — compose oscillator/filter/fx chains;
   reverb/delay/chorus/distortion; variant keywords in NL (mirrors the 3D recipe
   system).
4. **Formats** — OGG export (isolated optional dep); stereo ambience.
5. **Corpus + golden set** — N seeds × every category read as themselves; no
   silent/clipped/degenerate output.

## Notes

- Determinism: one `Generator(PCG64(seed))`, fixed sample dtype/format; CI diffs a
  fixture WAV SHA — added with S0.
- Prior art to lean on: `sfxr`/`bfxr` (the proven one-shot model) and Andy
  Farnell's *Designing Sound* patches, ported to numpy.
