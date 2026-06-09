# Authoring guide — adding to the creature library

How to extend the v2/v3 modular library: a new **variant**, a new **slot/organ**, a
new **body base**, or a named **preset**. The cookbook ([agent-cookbook.md](agent-cookbook.md))
is about *using* the library; this is about *growing* it.

The whole point of the architecture is that new content is **data, not machinery**:
you author bones in a local frame, expose sockets, register the kind, and the
unchanged pipeline (geometry → skin → uv → texture → animate → render) does the
rest. If you find yourself adding a second geometry path, stop — it belongs as data.

Everything lives in three files:

| File | What you touch |
|---|---|
| `pgap/v2/library.py` | the module (bones + sockets) and any recipe |
| `pgap/v2/registry.py` | register the kind / variant / template + height |
| `pgap/v2/nl.py` | optional natural-language keywords |

Then `tests/test_v3_corpus.py` gates it automatically, and `python -m pgap.catalog`
draws it into [BESTIARY.md](BESTIARY.md).

---

## The frame and conventions (read once)

- **Local frame:** every module is authored with its **root at the origin**, in
  **+X forward, +Y up, +Z left**. The assembler places the root at the parent's
  socket and composes transforms; you never think in world space.
- **A bone** is a tapered capsule. `BoneSpec(name, parent, head, tail, radius_head,
  radius_tail, group="none", fused=True, region=None)`:
  - `parent` is a *local* bone name, or `None` to attach at the module's root.
  - `fused=False` makes a **proud organ** — hard-min'd onto the body as a distinct
    bead instead of melting into the smooth-min surface (eyes, nose, stinger barb).
  - `region="eyes"|"nose"|"mouth"` paints the bone independently of the coat (see
    `pgap/palette.py`); leave `None` to take the coat color.
- **A socket** is `Socket(name, position, host_bone, mirror=False, ring=None,
  ring_radius=0.0)` — a named attach point on `host_bone` (local coords).
- **Socket-naming convention** — a name means the same thing on every body, so
  parts compose across creatures. Reuse these before inventing new ones:
  `neck, top, wings, shoulder, hip, tail, tip, base, ridge` (body/limbs) and
  `horns, ears, tusks, eyes, jaws, cheeks` (heads), `gills` (neck).
- **Determinism is non-negotiable.** No wall-clock, no RNG in geometry, no
  set/dict-ordering. Same (recipe, seed) → byte-identical output; the corpus checks
  it. Keep meshes within `triBudget` (the kernel backs off resolution, but author
  reasonable radii).
- **Helpers** in `library.py`: `v(x,y,z)`; `_bilateral(segments, group, region,
  fused)` emits a Z-mirrored `_l`/`_r` pair; `_chain(...)` builds a segment chain.

---

## 1. Add a *variant* to an existing slot

The smallest contribution. Say a new horn shape. Author the module, then add it to
the kind's variant table.

```python
# library.py — author it (a single curved spike; _bilateral if it's a pair)
def horn_spiral_module() -> Module:
    return Module("horn", [
        BoneSpec("horn", None, v(0, 0, 0), v(0.04, 0.28, 0.02), 0.022, 0.003, "horn"),
    ], {})
```

```python
# registry.py — add to the "horn" variant table
"horn": ModuleKind(default="unicorn", variants={
    "unicorn": lambda p: L.horn_unicorn_module(),
    ...
    "spiral": lambda p: L.horn_spiral_module(),   # <-- new
}),
```

That's it — `{"kind": "horn", "variant": "spiral", "attach": "head.horns"}` now
validates and builds, and the corpus tests it in isolation + on a host.

---

## 2. Add a new *slot* (organ) — the full loop

Worked example: a `fangs` slot (a pair of downward teeth at the mouth). This is the
end-to-end pattern the L3 slots followed.

```python
# library.py — a proud, dark, mirrored pair
def fangs_module() -> Module:
    seg = [("fang", None, v(0.02, -0.01, 0.02), v(0.04, -0.07, 0.02), 0.010, 0.002)]
    return Module("fangs", _bilateral(seg, group="fang", region="nose", fused=False), {})
```

```python
# registry.py — register the kind (one form ⇒ _single)
"fangs": _single(lambda p: L.fangs_module()),
```

If it needs a socket no head has yet, add one to each head module (`head_module`,
`draconic_head_module`, `cephalopod_head_module`) — but **prefer an existing
socket** (here `head.jaws` works, so no new socket needed).

Optional natural-language (free mode), in `nl.py::_compose_free`:

```python
if "fang" in text or "fanged" in text:
    modules.append({"id": "fangs", "kind": "fangs", "attach": "head.jaws"})
```

Use it from a preset or recipe: `Attachment("fangs", fangs_module(), parent="head",
parent_socket="jaws")`.

**Gates:** `test_v3_corpus` builds it in isolation automatically. Add a
host-composition check to `tests/test_slots.py` (build it on a body+neck+head and
assert the mesh is watertight, in budget, fully skinned).

---

## 3. Add a *body base* (a new root module)

A base is a root module that exposes the sockets a creature hangs off. See
`body_module` (quadruped), `spine_module` (biped), `serpent_body_module`,
`avian_torso_module`, `arachnid_body_module`, `hexapod_body_module`.

```python
def my_body_module() -> Module:
    bones = [BoneSpec("spine0", None, v(0, 0, 0), v(0.3, 0, 0), 0.12, 0.10, "spine"), ...]
    return Module("my_body", bones, sockets={
        "neck": Socket("neck", v(0.3, 0.05, 0), "spine0"),
        "hip":  Socket("hip",  v(0.0, -0.05, 0.10), "spine0", mirror=True),  # bilateral
        "legs": Socket("legs", v(0, 0, 0), "spine0", ring=6, ring_radius=0.07),  # radial
        "tail": Socket("tail", v(-0.02, 0.02, 0), "spine0"),
    })
```

- `mirror=True` on a socket is informational; the **attachment** drives mirroring.
- `ring=N` places N yaw-rotated copies (legs, tentacles, eyestalks). **Ring
  placements are leaves** — you can't attach children to a ring copy.

Register with `_single(lambda p: L.my_body_module())`, then build a recipe (next).

---

## 4. Add a named *preset* (a template)

A template is just a `Recipe` — an ordered list of `Attachment`s, root first. Each
`Attachment(id, module, parent, parent_socket, mirror=False, rotation=(0,0,0))`
plugs a module into a parent's socket.

```python
# library.py
def my_beast_recipe() -> Recipe:
    return Recipe("MyBeast", [
        Attachment("body", body_module()),
        Attachment("neck", neck_module(), parent="body", parent_socket="neck"),
        Attachment("head", head_module(), parent="neck", parent_socket="top"),
        _eyes_for("head"), _jaws_for("head"),                       # face helpers
        Attachment("horn", horn_bull_module(), parent="head", parent_socket="horns"),
        Attachment("leg", leg_module(), parent="body", parent_socket="hip", mirror=True),
    ])
```

```python
# registry.py — register the template + a display height
TEMPLATE_REGISTRY = { ..., "my_beast": lambda **o: L.my_beast_recipe() }
TEMPLATE_HEIGHT_CM = { ..., "my_beast": 140 }
```

- `_eyes_for(parent, variant, radius, spacing, aid)` and `_jaws_for(parent, ...,
  aid)` add a face; pass a unique `aid` for multi-headed creatures.
- Natural language (strict mode): add trigger phrases in `nl.py::_TEMPLATE_KEYWORDS`
  (matched on **word boundaries**, so short keys don't fire inside other words).
- Optional: add a coat/eye flavor in `pgap/catalog.py::_FLAVOR` so the gallery
  thumbnail looks good.

---

## Per-attachment rotation

`Attachment(..., rotation=(yaw, pitch, roll))` (degrees) pivots a module about its
socket — yaw about +Y, pitch about +Z, roll about +X. `(0,0,0)` is a no-op. On a
`mirror=True` attachment the right copy is auto Z-reflected so the pair stays
symmetric. Use it to fan parts (the hydra's three necks), sweep horns, or angle
limbs. It's also a recipe field: `"rotation": [yaw, pitch, roll]`.

---

## The contribution contract (what gates you)

Run the corpus — a new part is a small, reviewable change that *can't* break the
rest, because:

```bash
python -m pytest tests/test_v3_corpus.py   # every kind/variant + every template:
                                           # watertight, manifold, in budget, 4-skinned,
                                           # and deterministic (sha re-run)
python -m pytest                           # the whole suite
python -m pgap.cli --v2-capabilities       # confirm your kind/variant/socket shows up
python -m pgap.catalog                     # redraw docs/BESTIARY.md (review the diff)
```

The capability report (`pgap/v2/recipe.py::capability_report`) is the
machine-readable vocabulary an LLM/human authors against — your addition appears
there for free once registered.

---

## Checklist

- [ ] **Author** the module in `library.py` — root at origin, +X/+Y/+Z frame,
      reasonable radii. Use `fused=False` + `region` for proud/colored organs.
- [ ] **Sockets**: reuse a convention name; only add a new socket if none fits, and
      add it to *every* host of that type.
- [ ] **Register** in `registry.py` — `_single` for one form, a `ModuleKind`
      variant table for several, or `TEMPLATE_REGISTRY` + `TEMPLATE_HEIGHT_CM` for a
      preset.
- [ ] **NL** (optional): a template phrase in `_TEMPLATE_KEYWORDS`, or a slot
      keyword in `_compose_free`.
- [ ] **Test**: the corpus covers isolation + templates automatically; add a
      host-composition or structure check (`test_slots.py` / `test_presets.py` /
      `test_archetypes_v2.py`) for anything load-bearing.
- [ ] **Gallery**: `python -m pgap.catalog`; add a `_FLAVOR` entry for a preset.
- [ ] **Determinism**: no RNG/clock/ordering; `python -m pytest` green.
