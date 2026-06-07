"""Recipe JSON schema, fail-closed grammar validator, and v2/v3 capability report.

A recipe is a small JSON document an LLM/human authors:

    {
      "name": "MyBeast",
      "modules": [
        {"id": "body", "kind": "body"},
        {"id": "head", "kind": "head", "variant": "draconic", "attach": "body.neck"},
        {"id": "wings", "kind": "wing", "variant": "bat", "attach": "body.wings", "mirror": true}
      ],
      "seed": 5, "heightCm": 130, "material": {"baseColor": "teal"}
    }

`kind` chooses the slot; the optional `variant` chooses the form (V3). The
validator **fails closed** on unknown kind/variant, missing socket, dangling
parent, bad root count, or duplicate id. `capability_report` is the
machine-readable vocabulary (kinds + variants + sockets + params + templates).
"""

from __future__ import annotations

from typing import Any

from .registry import (
    MODULE_REGISTRY, TEMPLATE_REGISTRY, build_module, known_kind, resolve_kind,
    variant_names,
)
from .types import Attachment, Recipe


def _parse_attach(value: str):
    if not isinstance(value, str) or "." not in value:
        return None
    parent, socket = value.split(".", 1)
    return parent, socket


def validate_recipe(data: dict[str, Any]) -> dict:
    """Return ``{ok, errors, warnings}``. ``ok`` is False on any hard error."""
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict) or not isinstance(data.get("modules"), list) or not data["modules"]:
        return {"ok": False, "errors": ["recipe must have a non-empty 'modules' list"], "warnings": []}

    seen: dict[str, dict] = {}  # id -> module spec, in declared order
    roots = 0
    for i, m in enumerate(data["modules"]):
        if not isinstance(m, dict) or not m.get("id") or not m.get("kind"):
            errors.append(f"module #{i} needs an 'id' and a 'kind'")
            continue
        mid, kind = m["id"], m["kind"]
        if mid in seen:
            errors.append(f"duplicate module id {mid!r}")
            continue
        if not known_kind(kind):
            errors.append(f"unknown module kind {kind!r} (module {mid!r})")
            seen[mid] = m
            continue

        canon, forced = resolve_kind(kind)
        # variant: must exist for the kind (aliases force one, ignore provided).
        variant = m.get("variant")
        if forced is None and variant is not None and variant not in variant_names(kind):
            errors.append(f"module {mid!r}: unknown variant {variant!r} for {kind!r} "
                          f"(have {variant_names(kind)})")

        unknown = set(m.get("params") or {}) - set(MODULE_REGISTRY[canon].params)
        if unknown:
            warnings.append(f"module {mid!r}: ignored unknown params {sorted(unknown)}")

        attach = m.get("attach")
        if attach is None:
            roots += 1
        else:
            parsed = _parse_attach(attach)
            if parsed is None:
                errors.append(f"module {mid!r}: 'attach' must be '<parentId>.<socket>'")
            else:
                pid, socket = parsed
                if pid not in seen:
                    errors.append(f"module {mid!r}: attaches to unknown/earlier-undefined parent {pid!r}")
                elif known_kind(seen[pid]["kind"]):
                    p = seen[pid]
                    psockets = build_module(p["kind"], p.get("variant"), p.get("params")).sockets
                    if socket not in psockets:
                        errors.append(f"module {mid!r}: parent {pid!r} has no socket {socket!r} "
                                      f"(has {sorted(psockets)})")
                    elif psockets[socket].ring and m.get("mirror"):
                        warnings.append(f"module {mid!r}: mirror ignored on ring socket {socket!r}")
        seen[mid] = m

    if roots == 0:
        errors.append("recipe has no root module (exactly one module must omit 'attach')")
    elif roots > 1:
        errors.append(f"recipe has {roots} root modules (exactly one must omit 'attach')")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


def recipe_from_dict(data: dict[str, Any]) -> Recipe:
    """Build a validated ``Recipe`` from JSON. Raises ValueError if invalid."""
    report = validate_recipe(data)
    if not report["ok"]:
        raise ValueError("invalid recipe: " + "; ".join(report["errors"]))

    attachments = []
    for m in data["modules"]:
        module = build_module(m["kind"], m.get("variant"), m.get("params"))
        if m.get("attach") is None:
            attachments.append(Attachment(m["id"], module))
        else:
            pid, socket = _parse_attach(m["attach"])
            attachments.append(Attachment(m["id"], module, parent=pid,
                                          parent_socket=socket, mirror=bool(m.get("mirror"))))
    return Recipe(name=str(data.get("name", "Creature")), attachments=attachments)


def capability_report() -> dict:
    """Machine-readable vocabulary: kinds (+ variants), sockets, params, templates."""
    modules = {}
    for kind, mk in MODULE_REGISTRY.items():
        sockets = {sname: {"ring": bool(s.ring), "mirror": bool(s.mirror)}
                   for sname, s in build_module(kind).sockets.items()}
        modules[kind] = {
            "variants": list(mk.variants),
            "defaultVariant": mk.default,
            "sockets": sockets,
            "params": list(mk.params),
        }
    return {
        "schemaVersion": "pgap.v2.capabilities.v2",
        "modules": modules,
        "templates": list(TEMPLATE_REGISTRY),
        "recipeSchema": {
            "name": "str", "seed": "int", "heightCm": "number",
            "material": {"baseColor": "str"},
            "modules": [{"id": "str", "kind": "str", "variant": "str?",
                         "attach": "<parentId>.<socket>", "mirror": "bool?", "params": "object?"}],
        },
    }
