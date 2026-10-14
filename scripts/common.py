"""Shared paths and map bounds; all geometry comes from one configuration."""

import argparse
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def options(description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", type=Path, default=REPO / "config/map.json")
    parser.add_argument("--cache", type=Path, default=REPO / "cache")
    parser.add_argument("--output", type=Path, default=REPO / "build/YRD_1950")
    parser.add_argument("--font", type=Path, help="Path to a Chinese TTF/OTF/TTC font")
    return parser.parse_args()


def load_config(path):
    cfg = json.loads(path.read_text(encoding="utf-8"))
    assert cfg["resolution"] == int(cfg["game_side_m"] / 4) + 1
    assert 2 <= cfg["working_resolution"] <= cfg["resolution"]
    return cfg


def bounds(cfg):
    dy = cfg["real_side_m"] / 111320 / 2
    dx = dy / math.cos(math.radians(cfg["center_lat"]))
    return [
        cfg["center_lon"] - dx,
        cfg["center_lat"] - dy,
        cfg["center_lon"] + dx,
        cfg["center_lat"] + dy,
    ]


def find_font(explicit):
    paths = (
        [explicit]
        if explicit
        else [
            Path("C:/Windows/Fonts/msyh.ttc"),
            Path("/System/Library/Fonts/STHeiti Medium.ttc"),
            Path("/System/Library/Fonts/Supplemental/Songti.ttc"),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
        ]
    )
    for p in paths:
        if p.is_file():
            return p
    raise FileNotFoundError(
        "Chinese font not found. Supply --font PATH (e.g. Noto Sans CJK)."
    )
