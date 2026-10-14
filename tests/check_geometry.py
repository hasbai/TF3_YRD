"""Check rotated coordinates, download envelopes, and north-up compatibility."""

import math
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import bounds, corners, geo_to_local, local_to_geo  # noqa: E402

cfg = dict(center_lon=120.45, center_lat=31.17, real_side_m=380000)
for angle in [0, 10, -10, 45]:
    cfg["rotation_deg"] = angle
    half = cfg["real_side_m"] / 2
    x = np.array([-half, 0, half, -100000, 50000])
    y = np.array([half, 0, -half, 80000, -120000])
    lon, lat = local_to_geo(cfg, x, y)
    actual_x, actual_y = geo_to_local(cfg, lon, lat)
    np.testing.assert_allclose(actual_x, x, atol=1e-8)
    np.testing.assert_allclose(actual_y, y, atol=1e-8)
    west, south, east, north = bounds(cfg)
    for lon, lat in corners(cfg):
        assert west <= lon <= east and south <= lat <= north
    # Geographic north points right of screen-up for a positive rotation.
    nx, ny = geo_to_local(cfg, cfg["center_lon"], cfg["center_lat"] + 1)
    assert math.isclose(nx, 111320 * math.sin(math.radians(angle)), abs_tol=1e-8)
    assert math.isclose(ny, 111320 * math.cos(math.radians(angle)), abs_tol=1e-8)

cfg.pop("rotation_deg")
west, south, east, north = bounds(cfg)
dy = cfg["real_side_m"] / 111320 / 2
dx = dy / math.cos(math.radians(cfg["center_lat"]))
np.testing.assert_allclose(
    [west, south, east, north],
    [
        cfg["center_lon"] - dx,
        cfg["center_lat"] - dy,
        cfg["center_lon"] + dx,
        cfg["center_lat"] + dy,
    ],
)
print("Rotated coordinates and zero-degree compatibility passed")
