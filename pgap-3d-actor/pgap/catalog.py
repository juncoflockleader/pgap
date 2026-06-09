"""Bestiary catalog generator (roadmap 2, L5).

Builds every creature template, renders a deterministic thumbnail with the headless
software renderer (:mod:`pgap.render` — no engine needed), and writes a browsable
gallery markdown. So a human or an agent can *see* what the library can make, and
the gallery doubles as an at-a-glance visual regression: regenerate after any
change and diff the images.

Run: ``python -m pgap.catalog`` (writes ``docs/bestiary/*.png`` + ``docs/BESTIARY.md``).
Fully offline + deterministic (fixed seed, fixed camera) ⇒ stable output.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from . import palette
from .render import render_png
from .rng import make_rng
from .spec import Spec
from .v2.assembly import build_actor
from .v2.registry import TEMPLATE_HEIGHT_CM, TEMPLATE_REGISTRY, load_template

# Per-template (coat, eyeColor) flavor — chosen so each reads distinctly and the
# coat keyword maps to a real palette color. Deterministic; unlisted → the default.
_FLAVOR: dict[str, tuple] = {
    "biped": ("tan", "blue"), "beholder": ("stone", "red"), "kraken": ("stone", "amber"),
    "octopus_dragon": ("chocolate", "green"), "sphinx": ("golden", "amber"),
    "merfolk": ("cream", "green"), "cthulhu": ("stone", "green"),
    "unicorn": ("cream", "violet"), "stag": ("brown", "amber"), "boar": ("chocolate", "amber"),
    "horse": ("chocolate", "amber"), "feline": ("golden", "green"), "dragon": ("black", "red"),
    "serpent": ("golden", "amber"), "avian": ("cream", "amber"), "arachnid": ("black", "red"),
    "hexapod": ("chocolate", "green"), "centaur": ("tan", "blue"),
    "griffin": ("golden", "amber"), "manticore": ("chocolate", "red"),
    "wyvern": ("stone", "amber"), "pegasus": ("cream", "blue"), "hydra": ("stone", "green"),
    "naga": ("golden", "green"), "phoenix": ("golden", "amber"), "basilisk": ("stone", "red"),
    "chimera": ("golden", "amber"), "wolf": ("chocolate", "amber"),
}
_DEFAULT_FLAVOR = ("tan", None)


def _modules(name: str) -> list[str]:
    """Distinct module kinds composing a template, in attach order."""
    seen: list[str] = []
    for att in load_template(name).attachments:
        if att.module.kind not in seen:
            seen.append(att.module.kind)
    return seen


def _entry(name: str, img_dir: Path, size: int, seed: int) -> dict:
    coat, eye = _FLAVOR.get(name, _DEFAULT_FLAVOR)
    material = {"baseColor": coat}
    if eye:
        material["eyeColor"] = eye
    h = TEMPLATE_HEIGHT_CM[name]
    spec = Spec.from_dict({"name": name, "archetype": "biped", "species": name, "seed": seed,
                           "triBudget": 11000, "proportions": {"heightCm": h}, "material": material})
    skel, mesh = build_actor(load_template(name), spec, make_rng(spec.seed))
    tint = tuple(float(x) for x in palette.base_coat(material))
    (img_dir / f"{name}.png").write_bytes(render_png(mesh, size=size, tint=tint))
    return {"name": name, "bones": len(skel), "tris": mesh.num_triangles, "height": h,
            "coat": coat, "eye": eye or "dark", "modules": _modules(name)}


def _markdown(rows: list[dict], img_rel: str, img_w: int) -> str:
    out = [
        "# Bestiary",
        "",
        f"Auto-generated gallery of all **{len(rows)}** creature templates — built "
        "offline by the procedural pipeline and rendered headlessly "
        "(`pgap.render`, no engine). Regenerate with `python -m pgap.catalog`; do "
        "not hand-edit.",
        "",
        "| Preview | Creature | Bones · Tris · Height | Coat · Eyes | Modules |",
        "|:---:|---|---|---|---|",
    ]
    for r in rows:
        img = f'<img src="{img_rel}/{r["name"]}.png" width="{img_w}">'
        out.append(
            f'| {img} | **{r["name"]}** | {r["bones"]} · {r["tris"]} · {r["height"]:g} cm '
            f'| {r["coat"]} · {r["eye"]} | {", ".join(r["modules"])} |'
        )
    out.append("")
    return "\n".join(out)


def build_catalog(img_dir="docs/bestiary", md_path="docs/BESTIARY.md", size: int = 320,
                  img_w: int = 180, seed: int = 5, templates=None) -> list[dict]:
    """Render every template (or ``templates``) to ``img_dir`` and write the gallery
    markdown at ``md_path``. Returns the per-creature stat rows."""
    img_dir = Path(img_dir)
    md_path = Path(md_path)
    img_dir.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    names = list(templates) if templates is not None else list(TEMPLATE_REGISTRY)
    rows = [_entry(n, img_dir, size, seed) for n in names]
    img_rel = os.path.relpath(img_dir, md_path.parent).replace(os.sep, "/")
    md_path.write_text(_markdown(rows, img_rel, img_w))
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate the pgap bestiary gallery.")
    ap.add_argument("--img-dir", default="docs/bestiary")
    ap.add_argument("--md", default="docs/BESTIARY.md")
    ap.add_argument("--size", type=int, default=320)
    ap.add_argument("--seed", type=int, default=5)
    args = ap.parse_args(argv)
    rows = build_catalog(args.img_dir, args.md, size=args.size, seed=args.seed)
    print(f"wrote {len(rows)} thumbnails to {args.img_dir} and gallery {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
