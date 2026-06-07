# pgap-sound (psap) — Procedural Sound Asset Pipeline

Deterministic, offline synthesis of **game-ready sounds** — SFX, impacts, ambient
loops, and stylized creature vocals — exported as WAV. **Not music, not voice:
mainly sound.** The audio sibling of `pgap-3d-actor`, sharing its architecture,
determinism, and `unreal-mcp-rx` handoff.

Status: **planning.** The design lives in [PRD.md](PRD.md); the phased build plan
to a usable first version is in [MVP.md](MVP.md).

Run (once implemented) via the monorepo wrapper:

```bash
python pgap.py sound --describe "a retro coin pickup"
python pgap.py sound --spec laser.json --out out
```

Core thesis (Architecture B for audio): don't ask a model to *make* the sound —
**synthesize it** with classic DSP (oscillators, envelopes, filters, noise, modal
banks). Reproducible, free, lightweight; the deliberate trade is **synthesized,
not recorded**. See the [PRD](PRD.md) for goals/non-goals, the synth-module
architecture, and the sound taxonomy; see [MVP.md](MVP.md) for the phased build
order (S0–S5) and what's in/out of the first version.
