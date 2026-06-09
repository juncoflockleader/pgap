"""Gear spec schema + fail-closed validation."""

from __future__ import annotations

from typing import Any, Dict, List

from .registry import SIZE_SCALE, TEMPLATES, default_variant, is_template, variants_for

SIZES = tuple(SIZE_SCALE)

DEFAULTS: Dict[str, Any] = {
    "name": None,          # default derived from template
    "template": "sword",
    "variant": "auto",     # auto -> the template's default variant
    "material": "",        # freeform; keywords pick metal/grip/accent
    "size": "normal",
    "seed": 0,
}


def validate_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Return {ok, errors, warnings, normalized}. Fail-closed on unknown template."""
    errors: List[str] = []
    warnings: List[str] = []
    out = dict(DEFAULTS)
    out.update({k: v for k, v in (spec or {}).items() if v is not None})

    template = str(out.get("template", "")).strip().lower()
    out["template"] = template
    if not is_template(template):
        errors.append(f"unknown template {template!r}; choices: {sorted(TEMPLATES)}")
        return {"ok": False, "errors": errors, "warnings": warnings, "normalized": out}

    variant = str(out.get("variant", "auto")).strip().lower()
    if variant in ("auto", ""):
        variant = default_variant(template)
    elif variant not in variants_for(template):
        warnings.append(f"variant {variant!r} not in {variants_for(template)}; using default")
        variant = default_variant(template)
    out["variant"] = variant

    size = str(out.get("size", "normal")).strip().lower()
    if size not in SIZE_SCALE:
        warnings.append(f"size {size!r} not in {list(SIZE_SCALE)}; using normal")
        size = "normal"
    out["size"] = size

    out["material"] = str(out.get("material", "") or "")

    try:
        out["seed"] = int(out["seed"])
    except (TypeError, ValueError):
        errors.append("seed must be an integer")

    if not out.get("name"):
        out["name"] = "".join(w.capitalize() for w in (variant, template))

    return {"ok": not errors, "errors": errors, "warnings": warnings, "normalized": out}
