# pgap-sound (psap) — Procedural Sound Asset Pipeline

Deterministic, offline synthesis of **game-ready sounds** — SFX, impacts, ambient
loops, and stylized creature vocals — exported as WAV. **Not music, not voice:
mainly sound.** The audio sibling of `pgap-3d-actor`, sharing its architecture,
determinism, and `unreal-mcp-rx` handoff.

Status: **planning.** The design lives in [PRD.md](PRD.md).

Run (once implemented) via the monorepo wrapper:

```bash
python pgap.py sound --describe "a retro coin pickup"
python pgap.py sound --spec laser.json --out out
```

Core thesis (Architecture B for audio): don't ask a model to *make* the sound —
**synthesize it** with classic DSP (oscillators, envelopes, filters, noise, modal
banks). Reproducible, free, lightweight; the deliberate trade is **synthesized,
not recorded**. See the [PRD](PRD.md) for goals/non-goals, the synth-module
architecture, the sound taxonomy, and milestones M0–M5.
