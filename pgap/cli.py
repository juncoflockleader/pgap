"""CLI entry point: ``python -m pgap.cli --spec spec.json``.

Threads one seeded RNG through the M1 pipeline (skeleton → geometry → skin →
assemble) and writes the skinned glTF + import sidecar + manifest.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .animation import animate
from .assemble import write_outputs
from .geometry import mesh_stats
from .pipeline import build_actor
from .rng import make_rng
from .skinning import skin_stats
from .spec import Spec


def run(spec_path: str, out_dir: str) -> dict:
    spec = Spec.load(spec_path)
    rng = make_rng(spec.seed)  # the single generator for the whole run

    skel, mesh = build_actor(spec, rng)
    clips = animate(skel, spec)

    result = write_outputs(mesh, spec, out_dir, skel, clips)
    result["mesh_stats"] = mesh_stats(mesh)
    result["skin_stats"] = skin_stats(mesh)
    result["tri_budget"] = spec.tri_budget
    result["bones"] = len(skel)
    result["clips"] = [c.name for c in clips]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="build_procedural_actor",
        description="pgap M1 — generate a skinned quadruped glTF from a spec.",
    )
    parser.add_argument("--spec", required=True, help="path to the actor spec JSON")
    parser.add_argument("--out", default="out", help="output directory (default: ./out)")
    args = parser.parse_args(argv)

    if not Path(args.spec).is_file():
        parser.error(f"spec not found: {args.spec}")

    r = run(args.spec, args.out)
    ms, ss = r["mesh_stats"], r["skin_stats"]
    print(f"wrote {r['gltf']}")
    print(f"  sha1         {r['gltf_sha1']}")
    print(f"  bones        {r['bones']}")
    print(f"  vertices     {ms['vertices']}")
    print(f"  triangles    {ms['triangles']}  (budget {r['tri_budget']})")
    print(f"  boundary     {ms['boundary_edges']} edges   non-manifold {ms['nonmanifold_edges']} edges")
    print(f"  weight err   {ss['max_weight_error']:.2e}   max influences {ss['max_influences']}")
    print(f"  unweighted   {ss['unweighted_vertices']}   max joint idx {ss['max_joint_index']}")
    print(f"  clips        {', '.join(r['clips']) if r['clips'] else '(none)'}")
    if "import" in r:
        print(f"wrote {r['import']}")
    print(f"wrote {r['manifest']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
