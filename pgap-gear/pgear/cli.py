"""pgear CLI.

  python -m pgear.cli --capabilities
  python -m pgear.cli --gear sword --variant curved --material "iron, leather" --out out
  python -m pgear.cli --describe "a curved iron sword with a leather grip" --out out
  python -m pgear.cli --spec fixtures/sword.json --handoff --out out
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .capabilities import capabilities
from .pipeline import generate
from .registry import template_names
from .spec import SIZES, validate_spec


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pgear", description="pgap-gear — procedural gear (weapons + shields)")
    p.add_argument("--spec", help="path to a gear spec JSON")
    p.add_argument("--describe", help="natural-language prompt -> gear spec")
    p.add_argument("--gear", choices=template_names(), help="template (when not using --spec/--describe)")
    p.add_argument("--variant", help="variant for the template (default: the template default)")
    p.add_argument("--material", help="freeform material string (e.g. 'iron, leather, gold')")
    p.add_argument("--size", choices=SIZES, help="overall size")
    p.add_argument("--name", help="output asset name")
    p.add_argument("--seed", type=int, help="seed")
    p.add_argument("--out", default="out", help="output directory (default: out)")
    p.add_argument("--handoff", action="store_true", help="also emit the unreal-mcp-rx source bundle")
    p.add_argument("--capabilities", action="store_true", help="print the capability contract and exit")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.capabilities:
        print(json.dumps(capabilities(), indent=2))
        return 0

    if args.spec:
        spec = json.loads(Path(args.spec).read_text())
    elif args.describe:
        from .nl import prompt_to_spec
        res = prompt_to_spec(args.describe, seed=args.seed if args.seed is not None else 0)
        for w in res["warnings"]:
            print(f"warning: {w}", file=sys.stderr)
        spec = res["spec"]
    elif args.gear:
        spec = {"template": args.gear}
    else:
        print("provide --gear, --describe, or --spec (or --capabilities)", file=sys.stderr)
        return 2

    for key, val in (("variant", args.variant), ("material", args.material),
                     ("size", args.size), ("name", args.name)):
        if val is not None:
            spec[key] = val
    if args.seed is not None:
        spec["seed"] = args.seed

    check = validate_spec(spec)
    for w in check["warnings"]:
        print(f"warning: {w}", file=sys.stderr)
    if not check["ok"]:
        for e in check["errors"]:
            print(f"error: {e}", file=sys.stderr)
        return 2

    manifest, paths = generate(spec, args.out, handoff=args.handoff)
    n = check["normalized"]
    print(f"wrote {paths['mesh']}")
    print(f"  gear         {n['variant']} {n['template']} ({manifest['category']}, {n['size']})")
    print(f"  materials    {', '.join(manifest['materialSlots'].values())}")
    print(f"  triangles    {manifest['counts']['triangles']}")
    print(f"  preview      {paths['preview']}")
    if args.handoff:
        print(f"  handoff      {paths['handoff']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
