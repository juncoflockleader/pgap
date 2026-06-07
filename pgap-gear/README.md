# pgap-gear (pgear) — Procedural Gear Asset Pipeline

Deterministic, offline procedural generation of **equipment** — weapons, apparel,
armor, and accessories. The third pgap pipeline, sharing the family architecture
(spec/recipe → seeded RNG → module graph → render → glTF + manifest → engine
handoff).

Status: **placeholder / not started.** No PRD yet — `pgap-sound` is the next
pipeline to be built. This folder reserves the `gear` mode in the wrapper.

Run (once implemented) via the monorepo wrapper:

```bash
python pgap.py gear --describe "a curved iron sword with a leather grip"
```

Intended scope (to be designed): swords/axes/bows/staves, helmets/chestplates/
greaves, robes/cloaks/boots, shields, rings/amulets — composed from a curated
module library (blade + guard + grip + pommel; pauldron + cuirass + …) with
named variants, the same way `pgap-3d-actor` composes creatures. Many gear pieces
are *rigid static meshes* (no skin) — the simplest path in the family — while worn
apparel/armor attaches to a character skeleton (reusing `pgap-3d-actor`'s rigs).
