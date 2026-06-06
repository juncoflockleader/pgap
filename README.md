# pgap — Procedural Generative Asset Pipeline

Deterministic, dependency-free procedural generation of game-ready 3D actors —
geometry, skeleton, skin weights, animations, and textures — for Unreal Engine.

This is "Architecture B" from the `unreal-mcp-rx` 3D-generation analysis: rather
than calling an external text-to-3D service, `pgap` owns the whole stack so output
is offline, reproducible, and consistent in style (stylized, not photoreal). Text
and image generative AI are used only where they are actually good (parameter
inference, base-color textures) — never to produce 3D geometry, rigs, or
animations.

## Core idea: skeleton-first generation

Build the canonical skeleton first, synthesize geometry *around* the bones
(SDF / metaballs → marching cubes), and derive skin weights from distance-to-bone.
Rigging and skinning are then correct by construction, and animations retarget
trivially because every generated creature shares one bone topology.

## Status

Planning. The full spec lives in [PRD.md](PRD.md). No implementation yet.

## Relationship to unreal-mcp-rx

`pgap` produces glTF (skeletal mesh + skin + animations) plus textures and an
import-metadata sidecar. The `unreal-mcp-rx` MCP server provides the "last mile"
— import, material authoring, Blueprint assembly, behavior, and runtime proof —
which is already built and reused unchanged.

See [PRD.md](PRD.md) for the architecture, spec schema, milestones, and quality
bar.
