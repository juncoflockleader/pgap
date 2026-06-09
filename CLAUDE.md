# CLAUDE.md — pgap (monorepo)

Guidance for Claude working in this repository.

## What this is

`pgap` is a small **monorepo of procedural game-asset generators** that share one
philosophy and architecture: turn a spec/prompt into a game-ready asset by
**constructing it algorithmically** (not via a generative model), deterministically
and offline. "Architecture B" from the `unreal-mcp-rx` analysis.

```
pgap/
  pgap.py            # wrapper CLI: routes a mode to its sub-pipeline
  pgap-3d-actor/     # rigged/skinned/animated/textured creatures (glTF) — IMPLEMENTED
  pgap-sound/        # SFX/impacts/ambient/creature vocals (WAV) — PRD stage
  pgap-gear/         # weapons/apparel/armor/accessories (pgear) — IMPLEMENTED (rigid)
  pgap-landscape/    # biome terrain (heightmap+layers) — PRD + scaffold
  pgap-city/         # modular building kits + city layouts — PRD + scaffold
  README.md  AGENTS.md  CLAUDE.md  SPLIT.md
```

Each sub-pipeline is self-contained (its own package, CLI, tests, docs, PRD, and
`AGENTS.md` / `CLAUDE.md`). Read the relevant sub-pipeline's `PRD.md` before
designing or implementing in it.

**[SPLIT.md](SPLIT.md)** is the authority on the pgap ⇄ unreal-mcp-rx boundary
("what exists and where" vs "how it's realized" + the manifest-role contract).
Read it before designing any engine handoff.

## Shared design principles (do not violate without discussion)

- **Deterministic.** Same (spec, seed) → byte-identical output. One seeded RNG
  threaded through every stage; no wall-clock, no UUIDs, no set/dict-ordering
  nondeterminism. The core path makes no network calls. Determinism is testable —
  add a fixture-SHA check with any generation code.
- **Dependency-light.** Pure Python + numpy for the core. Output formats (glTF,
  WAV, …) written directly. No ML framework, no heavy engine.
- **Stylized, not photoreal / not recorded.** The deliberate trade for owning the
  stack offline. Hero/realistic assets are a separate path (external services),
  out of scope.
- **Composable + fail-closed.** Assets compose from a curated module library
  selected by a spec/recipe; a validator rejects unsupported requests (it does not
  guess). A machine-readable capability report is the vocabulary an LLM authors
  against.
- **Engine-neutral output + handoff.** Standard files + a provenance `manifest.json`.
  The `unreal-mcp-rx` MCP server provides the Unreal "last mile" (import, material/
  sound authoring, Blueprint assembly, runtime proof) — built and reused unchanged;
  do not reimplement it here. The bridge is swappable per engine.

## Conventions

- **Scaffold per pipeline, only when working on it.** Don't create empty trees or
  boilerplate in a not-yet-started pipeline unless asked.
- Commit messages: imperative subject; end with
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Default branch is `main`. Only commit/push when the user asks.
- `out/` and `artifacts/` (any subfolder) are gitignored scratch; `.mcp.json` is
  local machine wiring (gitignored).

## Pipeline-specific guidance

- **3d-actor:** see [pgap-3d-actor/CLAUDE.md](pgap-3d-actor/CLAUDE.md),
  [pgap-3d-actor/PRD.md](pgap-3d-actor/PRD.md), and `pgap-3d-actor/docs/`.
- **sound:** see [pgap-sound/PRD.md](pgap-sound/PRD.md).
- **gear:** rigid weapons + shields — [pgap-gear/PRD.md](pgap-gear/PRD.md), [pgap-gear/README.md](pgap-gear/README.md).
