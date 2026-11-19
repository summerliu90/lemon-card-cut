#!/usr/bin/env python3
"""05 剪辑缩放：统一从 tutorial-anim.json / defaults 读取，禁止写死 0.55/0.72。"""

from __future__ import annotations

import json
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ANIM = _HERE.parent / "rules" / "tutorial-anim.json"
_DEFAULTS = _HERE.parents[1] / "defaults.json"


def load_scales() -> dict:
    cfg: dict = {}
    if _DEFAULTS.exists():
        cfg.update(json.loads(_DEFAULTS.read_text(encoding="utf-8")))
    if _ANIM.exists():
        cfg.update(json.loads(_ANIM.read_text(encoding="utf-8")))
    return {
        "overlay_scale": float(cfg.get("overlay_scale", 0.95)),
        "sticker_scale": float(cfg.get("sticker_scale", 1.0)),
        "pair_scale": float(cfg.get("pair_scale", 0.47)),
        "sticker_display_max_s": float(cfg.get("sticker_display_max_s", 5)),
    }


if __name__ == "__main__":
    print(json.dumps(load_scales(), ensure_ascii=False, indent=2))
