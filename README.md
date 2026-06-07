# pgap — Procedural Generative Asset Pipeline

A family of **deterministic, dependency-light, offline** generators that turn a
spec or a prompt into **game-ready assets** — owning the whole stack instead of
calling an external generative service. Output is reproducible, free, and
consistent in style (stylized, not photoreal). The common thesis: don't ask a
model to *make* the asset — **construct it algorithmically**; an LLM only fills in
the parameters.

This repo is a small monorepo of pipelines that share that philosophy, that
architecture (spec/recipe → seeded RNG → module graph → render → file + manifest →
engine handoff), and a single wrapper CLI.

## Pipelines

| Mode | Folder | What it generates | Status |
|---|---|---|---|
| **`3d-actor`** | [pgap-3d-actor/](pgap-3d-actor/) | rigged / skinned / animated / textured creatures (glTF) | **Implemented** (v1+v2+v3, live-verified in UE 5.7) |
| **`sound`** | [pgap-sound/](pgap-sound/) | SFX / UI / creature vocals / impacts / ambient loops (WAV) — *not music, not voice* | **Implemented** (MVP + impacts + ambient + FX bus + variant adjectives + seeded variance) |
| **`gear`** | [pgap-gear/](pgap-gear/) | weapons / apparel / armor / accessories | Planned |

## Usage

One wrapper routes a mode to its sub-pipeline; all other args pass through:

```bash
python pgap.py 3d-actor --creature dragon --color crimson --out out
python pgap.py 3d-actor --describe "a deer-antlered dragon with feathered wings and tusks" --mode free
python pgap.py 3d-actor --v2-capabilities      # the machine-readable contract an LLM reads
python pgap.py sound --describe "a retro coin pickup"
python pgap.py sound --describe "a small dragon growl" --seed 4
python pgap.py sound --spec pgap-sound/fixtures/bark.json --handoff
python pgap.py --help                          # list modes
```

Each sub-pipeline is self-contained (its own package, CLI, tests, and docs); the
wrapper runs it with that folder as the working directory.

## Shared design (every pipeline)

- **Deterministic:** one seeded `PCG64` RNG threaded through every stage, never
  re-seeded; pure-function stages; I/O only at the edges. Same (spec, seed) →
  byte-identical output on any machine.
- **Dependency-light:** pure Python + numpy. No ML framework, no heavy engine. The
  "knowledge" is code + small data tables, not trained weights.
- **Composable & fail-closed:** assets are composed from a curated module library
  selected by a spec/recipe; a validator rejects unsupported requests (it does not
  guess). A capability report is the machine-readable vocabulary an LLM authors
  against.
- **Engine-neutral output + handoff:** standard formats (glTF, WAV, …) + a
  provenance manifest. The `unreal-mcp-rx` MCP server provides the Unreal "last
  mile" (import, material/sound authoring, Blueprint assembly, runtime proof); the
  bridge is swappable per engine.

## For AI agents

See **[AGENTS.md](AGENTS.md)** for how an LLM/agent drives the wrapper and each
pipeline. Each pipeline also has its own `AGENTS.md` with mode-specific schemas
and examples (e.g. [pgap-3d-actor/AGENTS.md](pgap-3d-actor/AGENTS.md)).

## Status

`3d-actor` is fully built and live-verified in Unreal Engine 5.7 (131 tests).
`sound` is at the PRD stage; `gear` is a placeholder. The trade is deliberate
across all of them: **stylized, owned, and offline** beats photoreal-via-service
for low-budget development.
