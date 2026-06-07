# pgap for AI agents (monorepo entry point)

pgap is a family of deterministic, offline procedural **asset generators** sharing
one architecture and one wrapper CLI. Your job, as an agent, is the same across
all of them: turn the user's request into a **spec/recipe** (parameters), let the
pipeline **construct** the asset, and (optionally) hand off to `unreal-mcp-rx` for
the engine last mile. **You never generate the asset content yourself** — you fill
in parameters; the pipeline is deterministic.

## Route by mode

```bash
python pgap.py <mode> [args...]
```

| Mode | Use it for | Status | Deep guide |
|---|---|---|---|
| `3d-actor` | a creature / character / prop (rigged, animated, textured glTF) | ready | [pgap-3d-actor/AGENTS.md](pgap-3d-actor/AGENTS.md) |
| `sound` | a sound effect / impact / ambient loop / stylized creature vocal | planned | pgap-sound/PRD.md |
| `gear` | a weapon / apparel / armor / accessory | planned | — |

`python pgap.py --help` lists modes; an unready mode prints a pointer to its PRD.

## The pattern (identical per pipeline)

1. **Discover** the capabilities — every pipeline exposes a machine-readable
   contract (e.g. `python pgap.py 3d-actor --v2-capabilities`). Read it at runtime;
   it is the source of truth for what's supported.
2. **Author** a spec/recipe JSON (or use the pipeline's NL inference, e.g.
   `--prompt` / `--describe`). Compose from the listed modules/variants.
3. **Validate** — the pipeline **fails closed** on unsupported requests (unknown
   archetype/module/variant, missing socket, …); it returns errors, not guesses.
   Surface the error and suggest the nearest supported option; don't retry blindly.
4. **Generate** — the CLI writes the asset file(s) + a provenance `manifest.json`
   under `--out`.
5. **Hand off (optional)** — import into Unreal via `unreal-mcp-rx`
   (`editor_asset_import`), or emit the source-handoff bundle (`--handoff`) for the
   project-clone proof lane.

## Determinism

Every pipeline threads one seeded RNG. **Same (spec, seed) → byte-identical
output.** Change the `seed` to get a variation; keep it to reproduce exactly.

## Scope boundary (important)

Each pipeline is **curated and stylized**, not open-vocabulary. Supported
archetypes / modules / variants are enumerated in the capability report; anything
outside fails closed by design. That is a feature (lightweight, reproducible), not
a limitation to work around. Tell the user when something is unsupported.

## Per-pipeline specifics

Read the mode's own `AGENTS.md` / `PRD.md` for its schemas and examples:
- **3d-actor:** v1 spec (archetype/traits/animations) and v2/v3 recipe (modules +
  variants + sockets). See [pgap-3d-actor/AGENTS.md](pgap-3d-actor/AGENTS.md) and
  [pgap-3d-actor/docs/agent-cookbook.md](pgap-3d-actor/docs/agent-cookbook.md).
- **sound / gear:** PRD-stage; consult their PRDs once implemented.
