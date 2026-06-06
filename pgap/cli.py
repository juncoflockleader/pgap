"""CLI entry point.

Generate from a spec file (``--spec``) or a natural-language prompt
(``--prompt``); print the capability contract with ``--capabilities``. Threads one
seeded RNG through the pipeline and writes the glTF (+ textures, import sidecar,
manifest, optional source-handoff bundle).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .assemble import write_outputs
from .capabilities import capability_report, validate_spec
from .geometry import mesh_stats
from .nl import prompt_to_spec
from .pipeline import build_bundle
from .rng import make_rng
from .skinning import skin_stats
from .spec import Spec


def generate(spec: Spec, out_dir: str) -> dict:
    rng = make_rng(spec.seed)  # the single generator for the whole run
    skel, mesh, clips, textures = build_bundle(spec, rng)
    result = write_outputs(mesh, spec, out_dir, skel or None, clips, textures)
    result["mesh_stats"] = mesh_stats(mesh)
    result["skin_stats"] = skin_stats(mesh) if mesh.weights is not None else None
    result["tri_budget"] = spec.tri_budget
    result["bones"] = len(skel)
    result["clips"] = [c.name for c in clips]
    result["archetype"] = spec.archetype
    return result


def run(spec_path: str, out_dir: str) -> dict:
    return generate(Spec.load(spec_path), out_dir)


def _print_result(r: dict) -> None:
    ms, ss = r["mesh_stats"], r["skin_stats"]
    print(f"wrote {r['gltf']}")
    print(f"  archetype    {r['archetype']}")
    print(f"  sha1         {r['gltf_sha1']}")
    print(f"  bones        {r['bones']}")
    print(f"  vertices     {ms['vertices']}")
    print(f"  triangles    {ms['triangles']}  (budget {r['tri_budget']})")
    print(f"  boundary     {ms['boundary_edges']} edges   non-manifold {ms['nonmanifold_edges']} edges")
    if ss is not None:
        print(f"  weight err   {ss['max_weight_error']:.2e}   max influences {ss['max_influences']}")
        print(f"  unweighted   {ss['unweighted_vertices']}   max joint idx {ss['max_joint_index']}")
    print(f"  clips        {', '.join(r['clips']) if r['clips'] else '(none)'}")
    if "baseColor" in r:
        print(f"wrote {r['baseColor']}")
    if "import" in r:
        print(f"wrote {r['import']}")
    print(f"wrote {r['manifest']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_procedural_actor",
        description="pgap — generate a procedural actor from a spec or prompt.",
    )
    parser.add_argument("--spec", help="path to the actor spec JSON")
    parser.add_argument("--prompt", help="natural-language prompt to infer a spec from")
    parser.add_argument("--seed", type=int, help="seed override (default 12345 for --prompt)")
    parser.add_argument("--out", default="out", help="output directory (default: ./out)")
    parser.add_argument("--capabilities", action="store_true", help="print the capability report and exit")
    parser.add_argument("--handoff", action="store_true", help="also emit the M5 source-handoff bundle")
    parser.add_argument("--package-root", default="/Game/Prototype/Dogs", help="Unreal package root for handoff")
    args = parser.parse_args(argv)

    if args.capabilities:
        print(json.dumps(capability_report(), indent=2))
        return 0

    if args.prompt:
        raw = prompt_to_spec(args.prompt, seed=args.seed if args.seed is not None else 12345)
        report = validate_spec(raw)
        for w in report["warnings"]:
            print(f"  warning: {w}", file=sys.stderr)
        if not report["ok"]:
            for e in report["errors"]:
                print(f"  error: {e}", file=sys.stderr)
            print("  (could not infer a supported actor from the prompt)", file=sys.stderr)
            return 2
        spec = Spec.from_dict(report["normalized"])
        print(f"prompt → {spec.archetype}/{spec.species} \"{spec.name}\"")
    elif args.spec:
        if not Path(args.spec).is_file():
            parser.error(f"spec not found: {args.spec}")
        spec = Spec.load(args.spec)
        if args.seed is not None:
            spec = Spec.from_dict({**_spec_as_dict(spec), "seed": args.seed})
    else:
        parser.error("provide --spec, --prompt, or --capabilities")

    r = generate(spec, args.out)
    _print_result(r)

    if args.handoff:
        from .handoff import export_source_bundle
        h = export_source_bundle(spec, args.out, package_root=args.package_root)
        print("handoff bundle:")
        print(f"  mesh       {h['mesh']}")
        print(f"  animation  {h['animation']}  (motion bone {h['tailMotionBone']})")
        print(f"  texture    {h['texture']}")
        print(f"  manifest   {h['manifest']}")
    return 0


def _spec_as_dict(spec: Spec) -> dict:
    return {
        "name": spec.name, "archetype": spec.archetype, "species": spec.species,
        "seed": spec.seed, "triBudget": spec.tri_budget, "proportions": spec.proportions,
        "traits": spec.traits, "targetSkeletonName": spec.target_skeleton,
        "tailBone": spec.tail_bone, "animations": spec.animations, "material": spec.material,
    }


if __name__ == "__main__":
    sys.exit(main())
