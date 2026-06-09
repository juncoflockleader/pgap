# pgap-gear (pgear) — Procedural Gear Asset Pipeline

Deterministic, offline procedural generation of **equipment** — weapons, apparel,
armor, and accessories. The third pgap pipeline, sharing the family architecture
(spec/recipe → seeded RNG → module graph → render → glTF + manifest → engine
handoff).

Status: **v1 implemented (G0).** Rigid static-mesh **weapons + shields** —
sword / greatsword / dagger / axe / spear / mace / staff / bow / shield — composed
from a module kit (blade + guard + grip + pommel; haft + head; …) with named
variants and a freeform material palette (metal / grip / accent / wood). Each piece
is a multi-material **static-mesh glTF** + a preview PNG + an import sidecar (pivot,
**grip** socket, bounds, materials) + a manifest. Deterministic and offline. Design:
[PRD.md](PRD.md). Boundary with the engine: repo-root `SPLIT.md`.

```bash
# from the repo root, via the wrapper:
python pgap.py gear --capabilities
python pgap.py gear --describe "a curved iron sword with a leather grip and gold guard"
python pgap.py gear --gear axe --variant double --material "bronze, dark wood" --out out
python pgap.py gear --spec pgap-gear/fixtures/sword.json --handoff --out out
```

Most gear is a *rigid static mesh* (no skin) — the simplest path in the family, and
what v1 ships. Worn apparel/armor that deforms with a body (skinned to a
`pgap-3d-actor` rig) is the later path (G2). The engine "last mile" — import,
material assignment, socket-equip on a character, PIE proof — is `unreal-mcp-rx`'s.

## Tests

```bash
cd pgap-gear && python -m pytest -q   # build validity + determinism + NL + capabilities
```
