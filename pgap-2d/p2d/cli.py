"""p2d CLI — `python -m p2d.cli` (or `python pgap.py 2d ...`)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .capabilities import capability_report
from .pipeline import generate


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="p2d", description="Procedural 2D Asset Pipeline — stylized portraits "
        "and battle backdrops (deterministic, offline).")
    p.add_argument("--spec", help="path to a spec JSON file")
    p.add_argument("--kind", choices=["portrait", "background"],
                   help="what to generate (when not using --spec)")
    p.add_argument("--archetype", help="portrait archetype (see --capabilities)")
    p.add_argument("--biome", help="background biome (see --capabilities)")
    p.add_argument("--seed", type=int, default=0, help="RNG seed (default 0)")
    p.add_argument("--size", type=int, help="portrait canvas size (default 512)")
    p.add_argument("--width", type=int, help="background width (default 1152)")
    p.add_argument("--height", type=int, help="background height (default 648)")
    p.add_argument("--name", help="override the output asset name")
    p.add_argument("--out", default="out", help="output directory (default ./out)")
    p.add_argument("--capabilities", action="store_true",
                   help="print the machine-readable capability report and exit")
    return p


def _spec_from_args(args) -> dict:
    if args.spec:
        spec = json.loads(Path(args.spec).read_text())
        if args.seed:
            spec["seed"] = args.seed
        if args.name:
            spec["name"] = args.name
        return spec
    spec: dict = {"kind": args.kind, "seed": args.seed}
    if args.name:
        spec["name"] = args.name
    if args.kind == "portrait":
        if args.archetype:
            spec["archetype"] = args.archetype
        if args.size:
            spec["size"] = args.size
    else:
        if args.biome:
            spec["biome"] = args.biome
        if args.width:
            spec["width"] = args.width
        if args.height:
            spec["height"] = args.height
    return spec


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    if args.capabilities:
        print(json.dumps(capability_report(), indent=2))
        return 0

    if not args.spec and not args.kind:
        print("error: provide --kind portrait|background or --spec FILE "
              "(or --capabilities)", file=sys.stderr)
        return 2

    try:
        manifest = generate(_spec_from_args(args), args.out)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    f = manifest["files"][0]
    print(f"wrote {Path(args.out) / f['path']}  ({f['width']}x{f['height']}, role={f['role']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
