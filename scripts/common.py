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


def geo_to_local(cfg, lon, lat):
    """Real metres in map axes; positive angle rotates geography clockwise."""
    east = (
        (lon - cfg["center_lon"]) * 111320 * math.cos(math.radians(cfg["center_lat"]))
    )
    north = (lat - cfg["center_lat"]) * 111320
    angle = math.radians(cfg.get("rotation_deg", 0))
    c, s = math.cos(angle), math.sin(angle)
    return c * east + s * north, -s * east + c * north


def local_to_geo(cfg, x, y):
    """Inverse of geo_to_local; also accepts NumPy arrays for DEM sampling."""
    angle = math.radians(cfg.get("rotation_deg", 0))
    c, s = math.cos(angle), math.sin(angle)
    east, north = c * x - s * y, s * x + c * y
    return (
        cfg["center_lon"] + east / (111320 * math.cos(math.radians(cfg["center_lat"]))),
        cfg["center_lat"] + north / 111320,
    )


def corners(cfg):
    half = cfg["real_side_m"] / 2
    return [
        list(local_to_geo(cfg, x, y))
        for x, y in [(-half, -half), (half, -half), (half, half), (-half, half)]
    ]


def bounds(cfg):
    """Axis-aligned download envelope, not the rotated map footprint."""
    points = corners(cfg)
    return [
        min(p[0] for p in points),
        min(p[1] for p in points),
        max(p[0] for p in points),
        max(p[1] for p in points),
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
