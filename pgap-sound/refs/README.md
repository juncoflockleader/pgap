# refs/ — reference samples (design-time only)

Small, **CC0 / public-domain** reference recordings, analyzed offline by
`psap.analyze` to *measure* synth parameters (so presets fit real sounds instead
of guessing). **The runtime never plays these back** — only the derived numbers
get baked into presets, so generation stays 100% synthesis: deterministic,
offline, no audio shipped in the product.

## impacts/

Six isolated impact one-shots (wood / metal / glass, two each) from **Kenney's
Impact Sounds** pack, licensed **CC0** (public-domain dedication — free for any
use, no attribution required; see `impacts/Kenney_License.txt`). Source:
<https://kenney.nl/assets/impact-sounds>. Converted to 44.1 kHz mono PCM16 WAV.

`impacts/measured_impacts.json` is the analyzer output (the "model"): per material,
`base_freq` + modal `partials [ratio, gain, decay_s]` + `transient`. These numbers
are baked into `psap/impact.py::MATERIAL_PRESETS` (wood/metal/glass).

Re-derive any material with:

```bash
python -m psap.analyze refs/impacts/wood_000.wav --material wood
```

## vocals/

`vocals/dog_bark.wav` — one isolated bark cut from **"Dog barking mono"** by
Brandon Morris (OpenGameArt), dual-licensed **CC0** / OGA-BY 3.0 (CC0 applies; we
credit the author regardless). `analyze_vocal` measured its pitch (f0 ≈ 235 Hz) and
**formants** (~700 / 860 / 1884 / 3031 Hz) — see `vocals/measured_vocals.json`.
Those formants are baked into `psap/vocal.py::VOCAL_PRESETS["bark"]`, shaped by the
formant filter bank (`dsp.formant_bank`).
