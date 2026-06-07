# pgap for AI agents

How an LLM/agent drives pgap to turn a request into a game-ready 3D actor. You
("the agent") supply **parameters**; pgap deterministically builds the 3D. You
never generate geometry yourself.

Companion to [ARCHITECTURE.md](docs/ARCHITECTURE.md) (why) and
[README.md](README.md) (overview). The **capability reports are the source of
truth** — always read them at runtime rather than trusting this doc's lists.

---

## 1. Your job

1. Turn the user's request into a **spec** (v1) or a **recipe** (v2/v3) — JSON.
2. **Validate** it against the capability report (or let the CLI validate; it
   fails closed).
3. Run the CLI to produce the glTF (+ textures, sidecar, manifest).
4. (Optional) Hand off to `unreal-mcp-rx` to import/assemble/prove in Unreal.

You may also just call the CLI with `--prompt`/`--describe` and let pgap's own
deterministic inference build the spec/recipe — useful as a fallback, but
authoring the JSON yourself gives you full control.

## 2. Pick the interface

| The user wants… | Use | Command |
|---|---|---|
| a dog / generic quadruped / biped / a prop | **v1 spec** | `--spec file.json` or `--prompt "…"` |
| a composite creature (wings + tentacles + horns, a beholder, a dragon) | **v2/v3 recipe** | `--recipe file.json`, `--creature <template>`, or `--describe "…"` |

Rule of thumb: if it's one of the three v1 archetypes with breed/trait variation,
use a **spec**. If it's a chimera or needs body-part variants, use a **recipe**.

## 3. Discover what's supported (do this first)

```bash
python -m pgap.cli --capabilities      # v1: archetypes, species w/ part libraries, traits, animations, coats, proportion ranges
python -m pgap.cli --v2-capabilities   # v2/v3: every module `kind`, its `variants`, `sockets` (ring/mirror), `params`, and the template list
```

Both return JSON. The v2 report is the grammar you compose recipes against: a
module is a slot (`kind`), a part's form is a `variant`, and children attach to a
parent's named `sockets`.

## 4. v1 spec schema

```jsonc
{
  "name": "GoldenRetriever",
  "archetype": "quadruped",          // prop | quadruped | biped   (others fail closed)
  "species": "dog",                  // "dog" has a breed part library; others = generic
  "seed": 12345,                     // determinism: same spec+seed -> identical bytes
  "proportions": { "bodyLength": 1.05, "legLength": 1.0, "neck": 0.95,
                   "tail": 1.15, "heightCm": 58 },   // clamped to supported ranges
  "traits": { "ears": "floppy", "snout": "medium", "tail": "feathered" },
  "material": { "baseColor": "warm golden, darker ears", "fur": true, "roughness": 0.9 },
  "animations": ["idle", "walk", "tail_wag", "bark_pose"],  // dropped if unavailable for archetype
  "triBudget": 9000,
  "targetSkeletonName": "SKEL_GoldenRetriever",
  "tailBone": "tail_01"
}
```

- `material.baseColor` is free text; coat is keyword-matched (golden/brown/black/
  cream/stone/wood). Region words like "darker ears" are honored via vertex tint.
- `validate_spec` clamps out-of-range proportions and drops unavailable
  animations (warnings), and **errors** on an unsupported archetype.

## 5. v2/v3 recipe schema

```jsonc
{
  "name": "AntleredDragon",
  "seed": 5, "heightCm": 130,
  "material": { "baseColor": "deep green" },
  "modules": [
    { "id": "body", "kind": "body" },                                   // exactly one root (no "attach")
    { "id": "neck", "kind": "dragon_neck", "attach": "body.neck" },
    { "id": "head", "kind": "head", "variant": "draconic", "attach": "neck.top" },
    { "id": "horns", "kind": "horn", "variant": "antler", "attach": "head.horns" },
    { "id": "wing", "kind": "wing", "variant": "feathered", "attach": "body.wings", "mirror": true },
    { "id": "legf", "kind": "leg", "attach": "body.shoulder", "mirror": true },
    { "id": "legh", "kind": "leg", "attach": "body.hip", "mirror": true }
  ]
}
```

Rules (the validator enforces all of these, fail-closed):
- exactly **one root** module (the one with no `attach`); all others
  `"attach": "<parentId>.<socket>"` referencing an **earlier** module's socket.
- `kind` must be registered; optional `variant` must exist for that kind (omit →
  default). `params` keys must be known (unknown → warning).
- `mirror: true` makes a bilateral pair (e.g. wings, legs). A **ring** socket
  (e.g. `orb.eyes_ring`) auto-expands into N radial copies — don't also mirror it.
- sockets are **variant-specific** (e.g. only `head` variant `cephalopod` exposes
  `head.face`).

Compose by: pick a root body (`body` horizontal quadruped/dragon, `spine` upright
biped, `orb` radial), add `neck`+`head`, then attach limbs/wings/tail/horns/etc.
to the body/head sockets. Read `--v2-capabilities` for the exact socket names.

## 6. Fail-closed contract

Always treat validation as authoritative:
- v1: `pgap.capabilities.validate_spec(dict) -> {ok, errors, warnings, normalized}`.
- v2/v3: `pgap.v2.recipe.validate_recipe(dict) -> {ok, errors, warnings}`.
- CLI: `--recipe`/`--describe`/`--prompt` print warnings to stderr and **exit 2**
  with an error if the request can't be honored (e.g. "a quartz crystal" → no
  supported creature). Surface the error to the user; do not retry blindly.

## 7. CLI reference

| Flag | Meaning |
|---|---|
| `--spec <f.json>` | build a v1 actor from a spec |
| `--prompt "<text>"` | infer a v1 spec from natural language |
| `--creature <name>` | build a v2/v3 preset template (strict) |
| `--recipe <f.json>` | build a v2/v3 creature from a recipe (free) |
| `--describe "<text>"` | infer a v2/v3 recipe from natural language |
| `--mode strict\|free` | `--describe` mode (default strict = nearest template) |
| `--seed <int>` | override the seed |
| `--color "<coat>"` | coat for `--creature` |
| `--out <dir>` | output directory (default `out/`) |
| `--capabilities` / `--v2-capabilities` | print the JSON contracts and exit |
| `--handoff` | also emit the unreal-mcp-rx source-handoff bundle |

## 8. Output contract

Every run writes, under `--out`:
- `<Name>.gltf` — self-contained (mesh + skin + animations + PBR material +
  embedded base-color texture).
- `<Name>_BaseColor.png` — the texture artifact.
- `<Name>.import.json` — sidecar (target skeleton, tail bone, bone list, clips).
- `manifest.json` — spec hash, seed, per-file SHA-1, license note.

With `--handoff`: `SK_<Name>.gltf`, `A_<Name>_TailWiggle.gltf`,
`T_<Name>_Fur_BaseColor.png`, and `<Name>.source_manifest.json` (the
`game.interactive_component_agent_source_manifest.v1` bundle the proof lane reads).

## 9. Handing off to Unreal (unreal-mcp-rx)

If a live UE editor + `unreal-mcp-rx` bridge is available:
1. Generate (optionally `--handoff`).
2. `editor_asset_import` the `.gltf` → creates SkeletalMesh/StaticMesh + Skeleton
   + AnimSequences + Texture + Material. Use `dry_run` first, then `confirm: true`.
   Keep `save: false` for a transient preview.
3. To place a **skeletal** creature in a level it needs a Blueprint wrapper (a
   bare SkeletalMeshActor can't be assigned a mesh via reflected properties) —
   that's the `bp_author` assembly step. Static props spawn directly.
4. For the full proof, fill the handoff manifest into `interactive_component_plan`
   and run the project-clone proof lane.

## 10. Gotchas

- **Stylized, not photoreal**, and **bounded**: only the registered archetypes /
  modules / variants exist. Novel-but-unsupported requests fail closed — that's by
  design. Surface it; suggest the nearest supported option.
- **Determinism:** change the `seed` to get a different texture/variation; the same
  seed always reproduces byte-identical output.
- **Thin parts** (wings/feathers/fins) read as stylized-rounded under the capsule
  SDF — intended (the project is deliberately lightweight; no flat-primitive).
- **Budget:** `triBudget` is a hard cap (resolution backs off to fit).

## 11. Worked examples

See [docs/agent-cookbook.md](docs/agent-cookbook.md) for prompt → spec/recipe
examples covering dogs, props, bipeds, and chimeras (beholder, dragon, mermaid,
a custom winged-tentacle aberration).
