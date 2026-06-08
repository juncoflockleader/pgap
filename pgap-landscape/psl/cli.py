"""psl CLI — mirrors the pgap-3d-actor / psap CLI shape.

  python -m psl.cli --capabilities
  python -m psl.cli --biome plain --out out
  python -m psl.cli --spec fixtures/plain.json --handoff --out out
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .capabilities import capabilities as capability_report
from .pipeline import generate
from .spec import BIOMES, validate_spec


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="psl", description="pgap-landscape — procedural biome terrain")
    p.add_argument("--spec", help="path to a landscape spec JSON")
    p.add_argument("--biome", choices=BIOMES, help="biome (when not using --spec)")
    p.add_argument("--name", help="output asset name")
    p.add_argument("--seed", type=int, help="override seed")
    p.add_argument("--resolution", type=int, help="heightmap resolution (N*N+1)")
    p.add_argument("--out", default="out", help="output directory (default: out)")
    p.add_argument("--handoff", action="store_true", help="also emit the unreal-mcp-rx source bundle")
    p.add_argument("--capabilities", action="store_true", help="print the capability contract and exit")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.capabilities:
        print(json.dumps(capability_report(), indent=2))
        return 0

    if args.spec:
        spec = json.loads(Path(args.spec).read_text())
    elif args.biome:
        spec = {"biome": args.biome, "name": args.name or args.biome.capitalize()}
    else:
        print("provide --spec or --biome (or --capabilities)", file=sys.stderr)
        return 2

    if args.name:
        spec["name"] = args.name
    if args.seed is not None:
        spec["seed"] = args.seed
    if args.resolution is not None:
        spec["resolution"] = args.resolution

    check = validate_spec(spec)
    for w in check["warnings"]:
        print(f"warning: {w}", file=sys.stderr)
    if not check["ok"]:
        for e in check["errors"]:
            print(f"error: {e}", file=sys.stderr)
        return 2

    manifest, paths = generate(spec, args.out, handoff=args.handoff)
    s = check["normalized"]
    print(f"wrote {paths['heightmap']}")
    print(f"  biome        {manifest['biome']}")
    print(f"  resolution   {s['resolution']}  ({s['sizeKm']} km, {s['heightScaleM']} m)")
    print(f"  layers       {', '.join(s['layers'])}")
    print(f"  sha1         {manifest['files'][paths['heightmap'].name]}")
    print(f"  seed         {manifest['seed']}")
    if args.handoff:
        print(f"  handoff      {paths['handoff']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
