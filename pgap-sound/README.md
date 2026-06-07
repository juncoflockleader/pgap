# pgap-sound (psap) — Procedural Sound Asset Pipeline

Deterministic, offline synthesis of **game-ready sounds** — SFX, UI blips, and
stylized creature vocals — exported as WAV. **Not music, not voice: mainly
sound.** The audio sibling of `pgap-3d-actor`, sharing its architecture,
determinism, and `unreal-mcp-rx` handoff.

Status: **MVP implemented** (S0–S5; 23 tests green). The design is in
[PRD.md](PRD.md); the phased plan and what's in/out of v1 is in [MVP.md](MVP.md).

## Usage

```bash
# from the repo root, via the wrapper:
python pgap.py sound --describe "a retro coin pickup"
python pgap.py sound --describe "a small dragon growl" --seed 4
python pgap.py sound --spec pgap-sound/fixtures/laser.json --handoff --out out
python pgap.py sound --capabilities          # the machine-readable contract

# or directly (from this folder):
python -m psap.cli --describe "a dog bark" --out out
```

Output: `<Name>.wav` (PCM16) + `manifest.json` (spec hash, seed, SHA, license).
`--handoff` also emits the `unreal-mcp-rx` audio-role bundle (`S_<Name>.wav` +
a `SoundWave` import sidecar) — the dog's bark, generated rather than placeholdered.

## What it can make (MVP)

- **SFX** — `laser`, `coin`, `pickup`, `powerup`, `jump`, `hit`, `explosion`
- **UI** — `blip`
- **Vocals** — `bark`, `growl`, `roar`, `chirp`, `squeak`
- **Impacts** (modal synthesis) — `wood`, `metal`, `glass`, `stone`
- **Ambient loops** (seamless) — `wind`, `rain`, `fire`, `water`, `hum`, `drone`

Drive them by name with `--describe` (keyword inference: size words scale pitch,
"retro/8-bit" adds bitcrush), or author a full `SoundSpec` JSON for exact control.
Unsupported requests **fail closed** (see `--capabilities`).

### Variation vs. determinism

Output is **deterministic** (same `spec`+`seed` → byte-identical WAV) but **not
fixed**: the seed is your variation knob. `variance` (0..1) applies a seeded
*humanization* — small per-seed jitter of pitch / decay / cutoff — so changing
`--seed` gives a different *take* of the same sound, even for tonal one-shots that
have no noise. `--describe` defaults to `variance 0.2`; `--spec` defaults to `0`
(exact). Set `--variance 0` to reproduce a preset byte-for-byte.

```bash
python pgap.py sound --describe "a laser zap" --seed 1   # a take
python pgap.py sound --describe "a laser zap" --seed 2   # a different take
python pgap.py sound --describe "a laser zap" --variance 0   # the exact preset
```

## How it works

Architecture B for audio: don't ask a model to *make* the sound — **synthesize it**
with classic DSP. A `SoundSpec` → one seeded `PCG64` RNG → category router
(SFX = oscillator + sweep/arpeggio + envelope + filter + noise + bitcrush; vocals =
FM + pitch contour + growl AM + noise rasp; impacts = a bank of decaying resonant
modes + a noise contact transient, mode ratios encoding the material; ambient =
filtered/granular noise + slow LFO, made **seamlessly loopable** by an equal-power
crossfade of the tail back over the head) → render (DC-removal, soft-limit, fades,
peak-normalize) → hand-written PCM16 WAV + manifest. Pure Python + numpy, no ML
framework, no network. **Same (spec, seed) → byte-identical WAV.**

The deliberate trade is **synthesized, not recorded** (stylized, not foley). Next:
a recipe grammar + effects (reverb/delay) and more presets — see [MVP.md](MVP.md).
