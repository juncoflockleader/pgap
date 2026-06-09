"""Top-down city-plan preview (a PNG): ground + streets + building footprints
colored by height, props as dots. A debug/inspection aid that makes a layout
legible at a glance — the meshes themselves are the bridge's job (C1+).

Pure numpy raster (filled rects), deterministic. Not an engine role; a preview.
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np

# per-zone base hue (sRGB); height scales brightness on top of this.
ZONE_COLOR = {
    "residential": (150, 138, 116),
    "market": (176, 150, 92),
    "civic": (140, 158, 184),
}
GROUND = (52, 62, 48)     # grass-ish margin
STREET = (66, 66, 70)     # asphalt
PROP = (240, 214, 78)     # prop dot


def render_plan(layout: Dict[str, Any], size_px: int = 768, margin_px: int = 12) -> np.ndarray:
    extent = layout.get("extentM")
    if extent:
        span_m = max(extent)
    else:
        cols, rows = layout["sizeBlocks"]
        pitch = float(layout["blockSizeM"]) + float(layout["streetWidthM"])
        span_m = max(cols, rows) * pitch + float(layout["streetWidthM"])
    inner = max(16, size_px - 2 * margin_px)
    scale = inner / span_m

    def px(m: float) -> int:
        return margin_px + int(round(m * scale))

    img = np.full((size_px, size_px, 3), GROUND, dtype=np.uint8)

    # streets (bands, per-segment width + extent)
    for st in layout["streets"]:
        sw = max(1, int(round(float(st.get("width_m", layout["streetWidthM"])) * scale)))
        a, b = px(st.get("from_m", 0.0)), px(st.get("to_m", span_m))
        if st["axis"] == "v":
            x = px(st["x_m"])
            img[max(0, a):b, max(0, x - sw // 2): x + sw - sw // 2] = STREET
        else:
            y = px(st["y_m"])
            img[max(0, y - sw // 2): y + sw - sw // 2, max(0, a):b] = STREET

    # building footprints, brightness ∝ height
    hmax = max((i["height_m"] for i in layout["instances"]), default=1.0) or 1.0
    for inst in layout["instances"]:
        cx, cy = px(inst["x"] / 100.0), px(inst["y"] / 100.0)   # cm -> m -> px
        fw = max(1, int(round(inst["footprint_m"][0] * scale)))
        fd = max(1, int(round(inst["footprint_m"][1] * scale)))
        x0, x1 = max(0, cx - fw // 2), min(size_px, cx + fw - fw // 2)
        y0, y1 = max(0, cy - fd // 2), min(size_px, cy + fd - fd // 2)
        if x1 <= x0 or y1 <= y0:
            continue
        t = float(inst["height_m"]) / hmax
        base = np.array(ZONE_COLOR.get(inst["zone"], (150, 150, 150)), dtype=np.float64)
        col = np.clip(base * (0.45 + 0.55 * t), 0, 255).astype(np.uint8)
        img[y0:y1, x0:x1] = col

    # props (intersections)
    for p in layout["props"]:
        x, y = px(p["x"] / 100.0), px(p["y"] / 100.0)
        img[max(0, y - 1): y + 2, max(0, x - 1): x + 2] = PROP

    return img
