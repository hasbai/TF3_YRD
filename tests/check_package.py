"""Check generated files, sampled game coordinates, and native Lua syntax."""

from pathlib import Path
import json
import struct
import sys
import numpy as np
from PIL import Image
from lupa.lua54 import LuaRuntime
from scipy.ndimage import distance_transform_edt, label

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
from common import options, load_config, bounds, corners, geo_to_local  # noqa: E402

args = options(__doc__)
cfg = load_config(args.config)
root = args.output
report = json.loads((root / "docs/离线检查.json").read_text(encoding="utf-8"))
assert report["status"] == "offline checks passed", report["failed_checks"]
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
assert manifest["reference_bbox_lon_lat"] == bounds(cfg)
assert manifest["rotation_deg"] == cfg.get("rotation_deg", 0)
assert manifest["map_corners_lon_lat"] == corners(cfg)
assert manifest["required_editor_settings"] == {
    "nameList": "::/names/china/china.names",
    "language": "zh_CN",
}
layout = json.loads((root / "docs/布局数据.json").read_text(encoding="utf-8"))
assert (
    len(layout["towns"]) == manifest["towns"]
    and len(layout["industries"]) == manifest["industries"]
)
png = root / "heightmaps/YRD_1950_7169.png"
towns = {p["name"]: p for p in layout["towns"]}
for town in towns.values():
    if town["population_reference"] is not None:
        expected = town["population_reference"] / cfg["reference_people_per_game_person"]
        assert abs(town["factor"] * 98 - expected) < 0.001, town["name"]
assert towns["上海"]["factor"] / towns["苏州"]["factor"] > 1.9
assert all(towns["上海"]["factor"] >= p["factor"] for p in towns.values())
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
    x, y = geo_to_local(cfg, point["placed_lon"], point["placed_lat"])
    scale = cfg["real_side_m"] / cfg["game_side_m"]
    x, y = x / scale, y / scale
    assert abs(x - point["x"]) < 0.001 and abs(y - point["y"]) < 0.001
biome = Image.open(root / "biomes/YRD_biomes.png")
assert biome.size == (width, height) and biome.mode == "L"
assert set(np.unique(np.asarray(biome))).issubset({26, 77, 128})
sea = np.asarray(Image.open(root / "docs/参考蒙版/YRD_sea.png")) > 0
water_code = (
    (cfg["water_level_m"] - cfg["height_min_m"])
    / (cfg["height_max_m"] - cfg["height_min_m"])
    * 65535
)
clearance = (
    distance_transform_edt(sea & (array < water_code))
    * cfg["game_side_m"]
    / (width - 1)
)
components, _ = label(clearance >= 16)
sea_component = None
checkpoints = json.loads(
    (REPO / "data/sea-navigation.json").read_text(encoding="utf-8")
)
for name, lon, lat in checkpoints:
    x, y = geo_to_local(cfg, lon, lat)
    column = round((x / cfg["real_side_m"] + 0.5) * (width - 1))
    row = round((0.5 - y / cfg["real_side_m"]) * (height - 1))
    assert 0 <= row < height and 0 <= column < width, name
    component = int(components[row, column])
    if sea_component is None:
        sea_component = component
    assert component > 0 and component == sea_component, (name, component)
print(
    f"Final PNG: {len(checkpoints)} sea checkpoints connected with 16 m bank clearance"
)
for path in root.rglob("*.md"):
    assert "{{" not in path.read_text(encoding="utf-8")
for path in root.rglob("*.json"):
    json.loads(path.read_text(encoding="utf-8"))
lua = LuaRuntime()
native = lua.execute(
    (root / "towns_industries/YRD_1950.lua").read_text(encoding="utf-8")
    + "\nreturn data()"
)
assert len(native["towns"]) == manifest["towns"]
assert len(native["industries"]) == manifest["industries"]
for index, expected in enumerate(layout["towns"], 1):
    imported = native["towns"][index]
    assert imported["name"] == expected["name"]
    assert abs(imported["sizeFactors"][2] - expected["factor"]) <= 0.000005
print("Native Lua syntax and town population factors passed")
names_fixture = args.cache / "check_names_fixture.lua"
names_fixture.write_text(
    "return {\n"
    + ",\n".join(
        "{ name = "
        + json.dumps(p["name"], ensure_ascii=False)
        + f", x = {p['x']:.2f}, y = {p['y']:.2f}, "
        + f'fileName = "::/industries/{p["key"]}/{p["key"]}.con" }}'
        for p in layout["industries"]
    )
    + "\n}",
    encoding="utf-8",
)
lua.globals().arg = lua.table_from(
    [
        (root / "docs/恢复产业名称.txt").as_posix(),
        names_fixture.as_posix(),
    ]
)
lua.globals().dofile = lambda path: lua.execute(Path(path).read_text(encoding="utf-8"))
lua.execute((REPO / "tests/check_industry_names.lua").read_text(encoding="utf-8"))
print(
    f"Exported PNG, coordinates, biomes, documents and {manifest['towns'] + manifest['industries']} placement samples passed"
)
