# pgap agent cookbook

Copy-paste examples for driving pgap as an agent. Pairs with
[AGENTS.md](../AGENTS.md). Every spec/recipe here is validated and builds; adapt
the parameters. Reminder: read `--capabilities` / `--v2-capabilities` at runtime —
the registries are the source of truth.

---

## v1 — archetype specs

### A golden retriever (the reference case)
```json
{
  "name": "GoldenRetriever", "archetype": "quadruped", "species": "dog", "seed": 12345,
  "proportions": { "bodyLength": 1.05, "legLength": 1.0, "neck": 0.95, "tail": 1.15, "heightCm": 58 },
  "traits": { "ears": "floppy", "snout": "medium", "tail": "feathered" },
  "material": { "baseColor": "warm golden, darker ears, cream chest", "fur": true },
  "animations": ["idle", "walk", "tail_wag", "bark_pose"], "triBudget": 9000
}
```
```bash
python -m pgap.cli --spec dog.json --out out
# equivalently, from text:
python -m pgap.cli --prompt "a small golden retriever with floppy ears that wags its tail and barks"
```

### A black, pointy-eared, long-bodied dog
Change `traits.ears` → `"pointy"`, `material.baseColor` → `"black"`,
`proportions.bodyLength` → `1.25`. Or: `--prompt "a long-bodied black dog with pointy ears"`.

### A prop (rigless static mesh)
```json
{ "name": "GraniteRock", "archetype": "prop", "species": "rock", "seed": 7,
  "proportions": { "heightCm": 50 },
  "material": { "baseColor": "grey granite stone", "fur": false, "roughness": 0.85 },
  "triBudget": 4000 }
```
`species` of `barrel` gives a barrel instead. `--prompt "a big grey mossy boulder"` works too.

### A biped
```json
{ "name": "SimpleBiped", "archetype": "biped", "species": "humanoid", "seed": 3,
  "proportions": { "heightCm": 180 }, "material": { "baseColor": "tan" },
  "animations": ["idle", "walk"], "triBudget": 8000 }
```

## v2/v3 — modular creature recipes

### Use a preset (strict) — fastest
```bash
python -m pgap.cli --creature beholder --color purple --out out
# templates: biped, beholder, kraken, octopus_dragon, sphinx, merfolk, cthulhu,
#            unicorn, stag, boar, horse, feline, dragon
```

### A beholder (radial — orb + central eye + a ring of eyestalks)
```json
{ "name": "Beholder", "seed": 5, "heightCm": 80, "material": { "baseColor": "violet" },
  "modules": [
    { "id": "orb", "kind": "orb", "params": { "eye_ring": 8 } },
    { "id": "eye", "kind": "eyeball", "attach": "orb.front" },
    { "id": "stalks", "kind": "eyestalk", "attach": "orb.eyes_ring" }
  ] }
```
`orb.eyes_ring` is a **ring socket** — the single `eyestalk` attachment expands to
8 radial copies. (A kraken is the same orb with `tentacle` on `orb.arms_ring`.)

### A classic dragon (the variant library at work)
```json
{ "name": "Dragon", "seed": 5, "heightCm": 140, "material": { "baseColor": "crimson" },
  "modules": [
    { "id": "body", "kind": "body" },
    { "id": "neck", "kind": "dragon_neck", "attach": "body.neck" },
    { "id": "head", "kind": "head", "variant": "draconic", "attach": "neck.top" },
    { "id": "horns", "kind": "horn", "variant": "bull", "attach": "head.horns" },
    { "id": "wing", "kind": "wing", "variant": "bat", "attach": "body.wings", "mirror": true },
    { "id": "legf", "kind": "leg", "attach": "body.shoulder", "mirror": true },
    { "id": "legh", "kind": "leg", "attach": "body.hip", "mirror": true },
    { "id": "tail", "kind": "serpent_tail", "attach": "body.tail" }
  ] }
```
Swap `wing.variant` to `feathered` and `horn.variant` to `antler` for a very
different beast — or just: `--describe "a deer-antlered dragon with feathered wings and tusks" --mode free`.

### A mermaid (upright torso + serpent tail + fin)
```json
{ "name": "Merfolk", "seed": 5, "heightCm": 175, "material": { "baseColor": "teal green" },
  "modules": [
    { "id": "spine", "kind": "spine" },
    { "id": "neck", "kind": "neck", "attach": "spine.neck" },
    { "id": "head", "kind": "head", "attach": "neck.top" },
    { "id": "arm", "kind": "arm", "attach": "spine.shoulder", "mirror": true },
    { "id": "tail", "kind": "serpent_tail", "attach": "spine.base" },
    { "id": "fin", "kind": "fin", "attach": "tail.tip" }
  ] }
```

### A horned horse with a mane and hooves
```json
{ "name": "WarHorse", "seed": 5, "heightCm": 160, "material": { "baseColor": "brown" },
  "modules": [
    { "id": "body", "kind": "body" },
    { "id": "neck", "kind": "neck", "attach": "body.neck" },
    { "id": "head", "kind": "head", "attach": "neck.top" },
    { "id": "horn", "kind": "horn", "variant": "ram", "attach": "head.horns" },
    { "id": "ears", "kind": "ear", "variant": "pointy", "attach": "head.ears" },
    { "id": "mane", "kind": "mane", "attach": "neck.mane" },
    { "id": "legf", "kind": "leg", "attach": "body.shoulder", "mirror": true },
    { "id": "legh", "kind": "leg", "attach": "body.hip", "mirror": true },
    { "id": "hooff", "kind": "hoof", "attach": "legf.tip", "mirror": true },
    { "id": "hoofh", "kind": "hoof", "attach": "legh.tip", "mirror": true }
  ] }
```
Note: `hoof`/`claw` attach to `leg.tip`; with `mirror: true` on a mirrored leg they
land on both sides — two attachments → four feet.

### A novel aberration (free composition)
```bash
python -m pgap.cli --describe "a floating orb with many eyestalks and tentacles" --mode free
python -m pgap.cli --describe "a winged humanoid with a fish tail" --mode free
```

## Prompt → what gets inferred (so you can predict it)

| Prompt fragment | Inference |
|---|---|
| dog / retriever / wolf / cat | quadruped (dog = breed library) |
| rock / boulder / barrel | prop |
| human / robot / person | biped (v1) or `spine` base (v2 free) |
| beholder / floating eye | orb + eyestalks |
| octopus / kraken / tentacle | tentacle ring |
| dragon / draconic | `body` base + `head:draconic` |
| antler / deer / stag | `horn:antler`; ram → `horn:ram`; unicorn → `horn:unicorn` |
| feathered / swan / angel wings | `wing:feathered`; bat → `wing:bat`; insect → `wing:insect` |
| tusks / boar | `tusk`; mane → `mane`; "pointy ears" → `ear:pointy` |
| golden / black / teal / crimson | coat keyword |
| giant / huge | larger; tiny / small → smaller |

If nothing matches, inference **fails closed** (exit 2) — tell the user it's
unsupported and suggest the nearest template or a `--free` composition.

## Tips

- **Strict for reliability, free for novelty.** `--creature`/strict templates are
  guaranteed recognizable; `--free` composes anything the grammar allows but the
  art is the author's responsibility.
- **One root, attach the rest.** Build outward from a body; read sockets from
  `--v2-capabilities`.
- **Determinism:** vary `seed` for texture/variation; keep it to reproduce.
- **Verify visually:** drop the `.gltf` into a glTF web viewer (it has an
  animation dropdown), or import into Unreal.
