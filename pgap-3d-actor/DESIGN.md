# Technical Design (lightweight)

Companion to [PRD.md](PRD.md). The PRD says *what/why and the milestones*; this
doc sketches *how* — module interfaces, the key algorithm per stage, the core
data structures, and the load-bearing technical decisions. It is intentionally
lightweight: guidance for whoever implements, not a frozen spec. Where this and
the PRD disagree, the PRD wins on scope; this doc wins on implementation detail.

## 1. Shape of the system

A pure function per stage, threaded by one seeded RNG, composed into a pipeline.
No hidden state, no globals, no I/O in the core (I/O only at the edges: read
spec, write glTF/PNG/manifest).

```
spec ─▶ route ─▶ skeleton ─▶ geometry ─▶ skin ─▶ uv ─▶ texture ─▶ animate ─▶ assemble ─▶ {gltf, png*, import.json, manifest}
                    │            │          │
              canonical rig   SDF field   distance-
              (per archetype) ↦ mesh      to-bone
```

Each stage is independently testable and cacheable by `hash(stage_inputs)`.

## 2. Module interfaces (indicative, not final)

```python
# determinism: one generator, passed explicitly, never re-seeded mid-run
Rng = numpy.random.Generator            # PCG64(seed)

@dataclass(frozen=True)
class Spec: ...                         # mirrors PRD §7 schema

@dataclass(frozen=True)
class Bone:                             # canonical rig node
    name: str; parent: str | None
    head: vec3; tail: vec3              # rest-pose segment, post-proportioning
    radius_head: float; radius_tail: float   # drives the SDF tube

Skeleton = list[Bone]                  # topologically sorted, root first

@dataclass(frozen=True)
class Mesh:
    positions: f32[N,3]; normals: f32[N,3]; indices: u32[M]
    uvs: f32[N,2] | None
    joints: u16[N,4] | None; weights: f32[N,4] | None

@dataclass(frozen=True)
class AnimClip:
    name: str
    channels: list[Channel]            # (bone, path=rotation|translation, times, values)

# stage signatures
route(spec) -> Archetype
build_skeleton(spec, rng) -> Skeleton
build_geometry(skel, spec, rng) -> Mesh          # positions+normals+indices only
skin(mesh, skel) -> Mesh                          # fills joints/weights
layout_uvs(mesh, archetype) -> Mesh               # fills uvs
synth_textures(spec, mesh, rng) -> dict[str, bytes]   # {"baseColor": png, ...}
animate(skel, spec) -> list[AnimClip]
assemble(mesh, skel, anims, textures, spec) -> Bundle # gltf + sidecar + manifest bytes
```

## 3. Stage notes (the load-bearing bits)

### Skeleton builder
- Canonical rig per archetype is **data**, not code: a fixed bone graph
  (quadruped: `pelvis → spine_n → neck → head`; four legs `hip/knee/ankle`; tail
  chain `tail_1..k`). Names are frozen — they are the contract with the animation
  library and the `import.json` sidecar.
- Proportioning = scale each bone's head/tail and radius from `spec.proportions`
  and `traits`. Output rest pose only. Keep it analytic and deterministic.

### Geometry kernel (the heart)
- Represent the body as a **signed distance field**: each bone segment is a
  tapered **capsule** SDF (point-to-segment distance minus an interpolated
  radius); ears/snout are extra capsules/spheres parented to head bones.
- Blend with **smooth-min** (polynomial smin, fixed `k`) so limbs fuse into one
  organic surface instead of separate boxes.
- Extract the surface with **marching cubes** over a voxel grid sized to the
  skeleton AABB + margin; grid resolution derived from `triBudget`. (Hand-rolled
  MC, or an optional `skimage.measure.marching_cubes` behind the same
  deterministic interface — pick one; keep numpy-only as the default.)
- Post: keep largest component, fill small holes, **manifold check** (reject +
  reseed on failure), **decimate** to the tri budget (quadric or vertex
  clustering), recompute normals. These checks are the FR4 gate.
- Why SDF over a part-assembly of boxes: smooth blending for free *and* it makes
  skinning trivial (next), because every surface point knows which bone(s)
  generated it.

### Skinning
- For each vertex: distance to each bone *segment* (reuse the capsule distance).
  Take the nearest 1–2 bones, weight by inverse distance (or a smooth falloff),
  cap at 4 influences, normalize. No separate auto-rigger, no heat solve in v1.
- Upgrade path if it looks pinched at joints: bone-glow / heat-diffusion weights.

### UV layout
- Per-archetype **fixed atlas**: reserved rectangles for body/head/legs/tail so
  textures are paint-targetable and stable across seeds. Project each region by
  its dominant axis (cylindrical for limbs, planar for flat parts). Determinism
  over perfection — seams are acceptable for stylized.

### Texture synth
- Base color: optional image-gen call painted into the atlas rectangles, **cached
  by `hash(spec.material, seed)`**, with a deterministic procedural fallback
  (gradient + value noise tinted by `material.baseColor`). This is the only stage
  that may touch the network; isolate it so the core stays offline/deterministic.
- Roughness/normal/AO: procedural (curvature/AO baked from the mesh; noise normal).

### Animation
- Library of **canonical clips authored once on the canonical rig** (idle, walk,
  run, tail_wag, bark_pose). Because every generated skeleton shares the bone
  topology, "retarget" is just scaling translation keys by the proportion deltas;
  rotations carry over unchanged.
- Simple periodic motions (tail_wag) may be **procedural** (sinusoidal rotation
  on the tail chain) — cheaper than authoring and trivially deterministic.

### Assembler
- Emit one glTF: mesh (POSITION/NORMAL/JOINTS_0/WEIGHTS_0/indices) + skin
  (joints, inverseBindMatrices) + animation channels. The repo already hand-writes
  glTF in `unreal_mcp_rx`; reuse that approach or a vetted writer.
- Also emit `<Name>.import.json` (target skeleton, tail bone, skeleton policy) and
  `manifest.json` (spec hash, seed, generator version, per-file SHA, license note).
- These three artifacts are the **entire contract** with `unreal-mcp-rx`; nothing
  downstream changes.

## 4. Determinism strategy
- One `Generator(PCG64(seed))`, passed explicitly; never reseed mid-pipeline.
- No iteration over `set`/`dict` for anything that affects output; sort first.
- Fixed float formatting and array dtypes in the glTF buffer.
- Test: a fixture spec re-run on a clean machine must produce an identical
  output SHA. Add this test alongside the first geometry code.

## 5. Key decisions & alternatives
| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Geometry repr | SDF capsules + smooth-min | box/part assembly; subdivision | smooth blend + free skinning |
| Surface extract | marching cubes | surface nets / dual contouring | simplest watertight; DC later for sharp features |
| Skinning | distance-to-bone | heat diffusion | robust, cheap; upgrade if pinching |
| Animation | canonical clips + scale; procedural for periodic | full IK / mocap | tractable; one rig topology makes retarget trivial |
| Deps | numpy core; MC/decimate optional | heavy graphics stack | offline, deterministic, portable |

## 6. Proposed layout (when implementation starts — not scaffolded now)
```
pgap/
  spec.py          # Spec dataclass + validation + capability report
  rng.py           # seeded RNG helpers
  archetypes/      # canonical rigs, part libraries, UV atlases (data)
  skeleton.py
  geometry.py      # SDF primitives, smooth-min, marching cubes, cleanup
  skinning.py
  uv.py
  texture.py
  animation.py     # clip library + retarget
  assemble.py      # glTF + import.json + manifest
  cli.py           # build_procedural_actor.py entrypoint
  tests/           # determinism, mesh validity, golden corpus
```

## 7. Testing
- **Determinism**: fixture spec → SHA stable across runs/machines.
- **Mesh validity**: manifold, watertight-enough, within tri budget, UVs in [0,1],
  weights normalized & ≤4 influences (the FR4/FR5 gates, run on every output).
- **Variance/golden corpus**: N seeds per species all import and read as the
  species; store reference renders/SHAs.
- **Integration**: regenerate the golden retriever and pass the existing
  `unreal-mcp-rx` project-clone proof lane (import + assembly + bark/tail-wag PIE).

## 8. Recommended build order
Follows PRD M0–M7: geometry kernel + determinism first (M0), then rig+skin (M1),
the dog library (M2), animations (M3), textures (M4), proof integration (M5),
other archetypes (M6), LLM front-end + corpus (M7). Get a recognizable dog
through the full proof lane before generalizing.
