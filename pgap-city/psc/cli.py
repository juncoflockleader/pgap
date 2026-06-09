"""psc CLI.

  python -m psc.cli --capabilities
  python -m psc.cli --era modern --culture american --out out
  python -m psc.cli --spec fixtures/american.json --handoff --out out
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .capabilities import capabilities as capability_report
from .pipeline import generate
from .spec import CULTURES, ERAS, validate_spec


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="psc", description="pgap-city — procedural modular cities")
    p.add_argument("--spec", help="path to a city spec JSON")
    p.add_argument("--describe", help="natural-language prompt -> city spec")
    p.add_argument("--era", choices=ERAS, help="era (when not using --spec)")
    p.add_argument("--culture", choices=CULTURES, help="culture/style (when not using --spec)")
    p.add_argument("--name", help="output city name")
    p.add_argument("--seed", type=int, help="override seed")
    p.add_argument("--blocks", type=int, nargs=2, metavar=("COLS", "ROWS"), help="city size in blocks")
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
    elif args.describe:
        from .nl import prompt_to_spec
        res = prompt_to_spec(args.describe, seed=args.seed if args.seed is not None else 0)
        for w in res["warnings"]:
            print(f"warning: {w}", file=sys.stderr)
        spec = res["spec"]
        print(f"describe -> {spec['era']}x{spec['culture']} {spec['sizeBlocks']}", file=sys.stderr)
    elif args.era and args.culture:
        spec = {"era": args.era, "culture": args.culture}
    else:
        print("provide --spec, --describe, or --era/--culture (or --capabilities)", file=sys.stderr)
        return 2

    if args.name:
        spec["name"] = args.name
    if args.seed is not None:
        spec["seed"] = args.seed
    if args.blocks is not None:
        spec["sizeBlocks"] = list(args.blocks)

    check = validate_spec(spec)
    for w in check["warnings"]:
        print(f"warning: {w}", file=sys.stderr)
    if not check["ok"]:
        for e in check["errors"]:
            print(f"error: {e}", file=sys.stderr)
        return 2

    manifest, paths = generate(spec, args.out, handoff=args.handoff)
    print(f"wrote {paths['layout']}")
    print(f"  cell         {manifest['cell']}")
    print(f"  blocks       {check['normalized']['sizeBlocks']}  (streetNet {check['normalized']['layout']})")
    print(f"  instances    {manifest['counts']['instances']}  props {manifest['counts']['props']}")
    print(f"  seed         {manifest['seed']}")
    if args.handoff:
        print(f"  handoff      {paths['handoff']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
