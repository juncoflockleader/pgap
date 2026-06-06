"""Archetype part libraries (data + builders) for the geometry kernel.

Each module exposes a ``build(skel, spec) -> list[Primitive]`` that returns extra,
non-bone SDF blobs positioned relative to the proportioned skeleton. M2 ships the
dog library; more breeds/archetypes land in M6.
"""
