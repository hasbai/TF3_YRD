"""Check generated files, sampled game coordinates, and native Lua syntax."""

from pathlib import Path
import json
import math
import shutil
import struct
import subprocess
import sys
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from common import options, load_config, bounds  # noqa: E402

args = options(__doc__)
cfg = load_config(args.config)
root = args.output
report = json.loads((root / "docs/离线检查.json").read_text(encoding="utf-8"))
assert report["status"] == "offline checks passed", report["failed_checks"]
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
assert manifest["reference_bbox_lon_lat"] == bounds(cfg)
layout = json.loads((root / "docs/布局数据.json").read_text(encoding="utf-8"))
assert (
    len(layout["towns"]) == manifest["towns"]
    and len(layout["industries"]) == manifest["industries"]
)
png = root / "heightmaps/YRD_1950_7169.png"
with png.open("rb") as file:
    header = file.read(29)
width, height, depth, color = struct.unpack(">IIBB", header[16:26])
assert (width, height, depth, color) == (cfg["resolution"], cfg["resolution"], 16, 0)
array = np.asarray(Image.open(png))
for point in layout["towns"] + layout["industries"]:
    column = round((point["x"] / cfg["game_side_m"] + 0.5) * (width - 1))
    row = round((0.5 - point["y"] / cfg["game_side_m"]) * (height - 1))
    elevation = (
        float(array[row, column]) / 65535 * (cfg["height_max_m"] - cfg["height_min_m"])
        + cfg["height_min_m"]
    )
    wet = point.get("on_water", False)
    assert (elevation < cfg["water_level_m"]) == wet, (point["name"], elevation)
    margin = 350 if wet else 500
    assert min(row, column, height - row - 1, width - column - 1) * 4 >= margin
    x = (
        (point["placed_lon"] - cfg["center_lon"])
        * 111320
        * math.cos(math.radians(cfg["center_lat"]))
        / (cfg["real_side_m"] / cfg["game_side_m"])
    )
    y = (
        (point["placed_lat"] - cfg["center_lat"])
        * 111320
        / (cfg["real_side_m"] / cfg["game_side_m"])
    )
    assert abs(x - point["x"]) < 0.001 and abs(y - point["y"]) < 0.001
biome = Image.open(root / "biomes/YRD_biomes.png")
assert biome.size == (width, height) and biome.mode == "L"
assert set(np.unique(np.asarray(biome))).issubset({26, 77, 128})
for path in root.rglob("*.md"):
    assert "{{" not in path.read_text(encoding="utf-8")
for path in root.rglob("*.json"):
    json.loads(path.read_text(encoding="utf-8"))
lua = shutil.which("lua")
if lua:
    script = "dofile(arg[1]);local m=data();assert(#m.towns==tonumber(arg[2]));assert(#m.industries==tonumber(arg[3]));print('Native Lua syntax passed')"
    checker = args.cache / "check_layout.lua"
    checker.parent.mkdir(exist_ok=True, parents=True)
    checker.write_text(script, encoding="utf-8")
    subprocess.run(
        [
            lua,
            str(checker),
            str(root / "towns_industries/YRD_1950.lua"),
            str(manifest["towns"]),
            str(manifest["industries"]),
        ],
        check=True,
    )
else:
    print("Lua executable unavailable: native syntax check not run")
print(
    f"Exported PNG, coordinates, biomes, documents and {manifest['towns'] + manifest['industries']} placement samples passed"
)
