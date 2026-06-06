"""Part-library dispatch (M2).

Routes a spec to its archetype/species part builder and returns the extra SDF
``Primitive`` blobs the geometry kernel blends with the bone capsules. Unknown
species return no parts (the bare skeleton blob, i.e. M1 behavior).
"""

from __future__ import annotations

from .archetypes import dog
from .spec import Spec
from .types import Bone, Primitive

# species -> builder. Extend in M6 for more breeds/archetypes.
_BUILDERS = {
    "dog": dog.build,
}


def build_parts(skel: list[Bone], spec: Spec) -> list[Primitive]:
    builder = _BUILDERS.get(str(spec.species).lower())
    if builder is None:
        return []
    return builder(skel, spec)
