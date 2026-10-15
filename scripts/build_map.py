"""Build a TF3 import package from cached geodata. No game installation required."""

import csv
import json
import math
import struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import (
    map_coordinates,
    gaussian_filter,
    distance_transform_edt,
    label,
)

from common import (
    options,
    load_config,
    bounds,
    corners,
    geo_to_local,
    local_to_geo,
    find_font,
    REPO,
)
import shutil

ARGS = options(__doc__)
CFG = load_config(ARGS.config)
CACHE = ARGS.cache
OUT = ARGS.output
N = CFG["working_resolution"]
FINAL = CFG["resolution"]
GAME_SIDE = float(CFG["game_side_m"])
REAL_SIDE = float(CFG["real_side_m"])
CLAT, CLON = CFG["center_lat"], CFG["center_lon"]
SCALE = REAL_SIDE / GAME_SIDE
WEST, SOUTH, EAST, NORTH = bounds(CFG)
MIN_HEIGHT, MAX_HEIGHT, WATER_LEVEL = (
    CFG["height_min_m"],
    CFG["height_max_m"],
    CFG["water_level_m"],
)
FONT_PATH = find_font(ARGS.font)
layout = json.loads((REPO / "data/layout.json").read_text(encoding="utf-8"))
towns, industries = [], []
for t in layout["towns"]:
    name, lon, lat, factor, com, ind, pop, year, basis = t
    if factor is None:
        factor = pop / CFG["reference_people_per_game_person"] / 98
    towns.append(
        dict(
            name=name,
            lon=lon,
            lat=lat,
            factor=factor,
            com=com,
            ind=ind,
            population_reference=pop,
            reference_year=year,
            population_basis=basis,
            initial_people_estimated=round(factor * 98),
        )
    )
for t in layout["industries"]:
    id_, name, key, lon, lat, basis = t
    industries.append(
        dict(
            id=id_,
            name=name,
            key=key,
            lon=lon,
            lat=lat,
            on_water=key in ["fishing_grounds", "oil_platform"],
            basis=basis,
        )
    )


def pixels(lon, lat):
    x, y = geo_to_local(CFG, lon, lat)
    return (
        (x / REAL_SIDE + 0.5) * (N - 1),
        (0.5 - y / REAL_SIDE) * (N - 1),
    )


def xy(lon, lat):
    x, y = geo_to_local(CFG, lon, lat)
    return x / SCALE, y / SCALE


def world_from_pixel(col, row):
    return ((col / (N - 1) - 0.5) * GAME_SIDE, (0.5 - row / (N - 1)) * GAME_SIDE)


def read_dem():
    manifest = json.loads((CACHE / "dem_manifest.json").read_text(encoding="utf-8"))
    assert manifest["bbox"] == bounds(CFG), "DEM/config extent mismatch"
    assert manifest["zoom"] == CFG["dem_zoom"], "DEM zoom mismatch"
    zoom = manifest["zoom"]
    jobs = manifest["tiles"]
    x0, y0 = min(j[0] for j in jobs), min(j[1] for j in jobs)
    x1, y1 = max(j[0] for j in jobs), max(j[1] for j in jobs)
    mosaic = np.zeros(((y1 - y0 + 1) * 256, (x1 - x0 + 1) * 256), dtype=np.float32)
    for x, y in jobs:
        rgb = np.asarray(
            Image.open(CACHE / f"dem/{zoom}_{x}_{y}.png"), dtype=np.float32
        )
        dem = rgb[:, :, 0] * 256 + rgb[:, :, 1] + rgb[:, :, 2] / 256 - 32768
        mosaic[
            (y - y0) * 256 : (y - y0 + 1) * 256, (x - x0) * 256 : (x - x0 + 1) * 256
        ] = dem
    local_x = np.linspace(-REAL_SIDE / 2, REAL_SIDE / 2, N)
    local_y = np.linspace(REAL_SIDE / 2, -REAL_SIDE / 2, N)
    heights = np.empty((N, N), dtype=np.float32)
    for start in range(0, N, 128):
        yy, xx = np.meshgrid(local_y[start : start + 128], local_x, indexing="ij")
        lons, lats = local_to_geo(CFG, xx, yy)
        xs = (lons + 180) / 360 * 2**zoom * 256 - x0 * 256 - 0.5
        ys = (
            (1 - np.arcsinh(np.tan(np.radians(lats))) / np.pi) / 2 * 2**zoom * 256
            - y0 * 256
            - 0.5
        )
        assert xs.min() >= 0 and xs.max() < mosaic.shape[1] - 1
        assert ys.min() >= 0 and ys.max() < mosaic.shape[0] - 1
        heights[start : start + 128] = map_coordinates(
            mosaic, [ys, xs], order=1, mode="nearest"
        )
    return gaussian_filter(heights, 0.7)


def intersects(points):
    xs, ys = zip(*[(p[0], p[1]) for p in points])
    return max(xs) >= WEST and min(xs) <= EAST and max(ys) >= SOUTH and min(ys) <= NORTH


def polygon(draw, rings, value):
    if not rings or not intersects(rings[0]):
        return
    draw.polygon([pixels(p[0], p[1]) for p in rings[0]], fill=value)
    for ring in rings[1:]:
        draw.polygon([pixels(p[0], p[1]) for p in ring], fill=255 - value)


def line(draw, points, width_m):
    if len(points) < 2 or not intersects(points):
        return
    vertices = [tuple(round(v) for v in pixels(*p)) for p in points]
    width = max(2, round(width_m / (GAME_SIDE / (N - 1))))
    draw.line(
        vertices,
        fill=255,
        width=width,
        joint="curve",
    )
    # Round joins close the single-pixel holes Pillow can leave at sharp bends.
    radius = (width - 1) / 2
    for x, y in vertices:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)


def water_masks():
    land_image = Image.new("L", (N, N), 0)
    draw = ImageDraw.Draw(land_image)
    for f in json.loads((CACHE / "ne_10m_land.geojson").read_text(encoding="utf-8"))[
        "features"
    ]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for rings in polys:
            polygon(draw, rings, 255)
    sea = np.asarray(land_image) == 0
    lake_image = Image.new("L", (N, N), 0)
    draw = ImageDraw.Draw(lake_image)
    lakes = []
    for f in json.loads((CACHE / "ne_10m_lakes.geojson").read_text(encoding="utf-8"))[
        "features"
    ]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for rings in polys:
            if intersects(rings[0]):
                polygon(draw, rings, 255)
                lakes.append(f["properties"].get("name") or "unnamed lake or reservoir")
    river_image = Image.new("L", (N, N), 0)
    draw = ImageDraw.Draw(river_image)
    routes = []
    waterways = json.loads((REPO / "data/waterways.geojson").read_text(encoding="utf-8"))
    for feature in waterways["features"]:
        props = feature["properties"]
        points = feature["geometry"]["coordinates"]
        width = props["width_game_m"]
        routes.append([props["name"], width, points])
        line(draw, points, width)
    water = sea | (np.asarray(lake_image) > 0) | (np.asarray(river_image) > 0)
    return water, sea, np.asarray(river_image) > 0, lakes, routes


def settle(item, height, water, placements, radius, margin):
    c, r = pixels(item["lon"], item["lat"])
    pixel_m = GAME_SIDE / (N - 1)
    candidates = []
    search_px = round(320 / pixel_m)
    step_px = max(1, round(16 / pixel_m))
    for dc in range(-search_px, search_px + 1, step_px):
        for dr in range(-search_px, search_px + 1, step_px):
            rr, cc = round(r + dr), round(c + dc)
            if min(rr, cc, N - 1 - rr, N - 1 - cc) * pixel_m < margin:
                continue
            is_water = item.get("on_water", False)
            if bool(water[rr, cc]) != is_water:
                continue
            rad = round(radius / pixel_m)
            w = water[max(0, rr - rad) : rr + rad + 1, max(0, cc - rad) : cc + rad + 1]
            if w.mean() < 0.97 if is_water else w.any():
                continue
            x, y = world_from_pixel(cc, rr)
            if any(
                math.hypot(x - p["x"], y - p["y"]) < (450 if "factor" in p else 390)
                for p in placements
            ):
                continue
            h = height[max(0, rr - rad) : rr + rad + 1, max(0, cc - rad) : cc + rad + 1]
            relief = float(h.max() - h.min())
            candidates.append((math.hypot(dc, dr) * pixel_m + relief * 8, rr, cc))
    if not candidates:
        raise RuntimeError("No valid location for " + item["name"])
    _, r, c = min(candidates)
    item["x"], item["y"] = world_from_pixel(c, r)
    item["pixel_col"], item["pixel_row"] = c, r
    item["position_shift_m"] = round(
        math.hypot(
            item["x"] - xy(item["lon"], item["lat"])[0],
            item["y"] - xy(item["lon"], item["lat"])[1],
        ),
        1,
    )
    item["placed_lon"], item["placed_lat"] = local_to_geo(
        CFG, item["x"] * SCALE, item["y"] * SCALE
    )
    if not item.get("on_water", False):
        flat_radius = round(radius / pixel_m)
        blend_width = max(2, round(64 / pixel_m))
        blend_radius = flat_radius + blend_width
        r0, r1 = max(0, r - blend_radius), min(N, r + blend_radius + 1)
        c0, c1 = max(0, c - blend_radius), min(N, c + blend_radius + 1)
        yy, xx = np.ogrid[r0:r1, c0:c1]
        dist = np.hypot(xx - c, yy - r)
        blend = np.clip((blend_radius - dist) / blend_width, 0, 1).astype(np.float32)
        blend[water[r0:r1, c0:c1]] = 0
        target = max(3, float(height[r, c]))
        height[r0:r1, c0:c1] = height[r0:r1, c0:c1] * (1 - blend) + target * blend
    placements.append(item)


def biome_map(real_dem, water, placements):
    rng = np.random.default_rng(CFG["seed"])
    coarse = rng.random((110, 110)).astype(np.float32)
    noise = np.asarray(Image.fromarray(coarse).resize((N, N), Image.Resampling.BICUBIC))
    forest = (
        ((real_dem > 130) & (noise > 0.24))
        | ((real_dem > 45) & (noise > 0.64))
        | ((real_dem > 5) & (noise > 0.88))
    )
    biomes = np.full((N, N), 26, dtype=np.uint8)
    biomes[forest & ~water] = 77
    bank_distance = distance_transform_edt(~water)
    biomes[(bank_distance < 4) & (~water)] = 128
    for p in placements:
        if p.get("on_water", False):
            continue
        radius = (
            360
            if "factor" in p
            else (320 if p["key"] in ["farm", "cotton_farm", "livestock_farm"] else 170)
        )
        c, r = p["pixel_col"], p["pixel_row"]
        k = round(radius / (GAME_SIDE / (N - 1)))
        yy, xx = np.ogrid[
            max(0, r - k) : min(N, r + k + 1), max(0, c - k) : min(N, c + k + 1)
        ]
        target = biomes[
            max(0, r - k) : min(N, r + k + 1), max(0, c - k) : min(N, c + k + 1)
        ]
        target[(xx - c) ** 2 + (yy - r) ** 2 <= k * k] = 26
    biomes[water] = 26
    return biomes


def export_lua():
    lines = [
        f"-- YRD 1950 / Gigantomaniac 1:1 / map axes x right, y up; geography clockwise {CFG.get('rotation_deg', 0)} deg",
        f"-- Reference population scale: {CFG['reference_people_per_game_person']} people per estimated game resident; factors use the Map Studio estimate of 98 residents per unit.",
        "function data()",
        "return {",
        "  towns = {",
    ]
    for p in towns:
        lines += [
            f"    -- {p['population_basis']}",
            "    { name = " + json.dumps(p["name"], ensure_ascii=False) + ",",
            f"      position = {{ x = {p['x']:.2f}, y = {p['y']:.2f} }},",
            f"      sizeFactors = {{ 1.00, {p['factor']:.5f}, 1.00 }},",
            f'      landUse2CargoNeedsCategories = {{ com = {{ {{ "{p["com"]}", 1.0 }} }}, ind = {{ {{ "{p["ind"]}", 0.5 }} }} }} }},',
        ]
    lines += ["  },", "  industries = {"]
    for p in industries:
        key = p["key"]
        lines += [
            f"    -- {p['id']} {p['name']}: {p['basis']}",
            f'    {{ angle = 0.0, fileName = "::/industries/{key}/{key}.con",',
            f'      onWater = {str(p["on_water"]).lower()}, position = {{ x = {p["x"]:.2f}, y = {p["y"]:.2f} }}, tag = "{key}" }},',
        ]
    lines += ["  }", "}", "end", ""]
    (OUT / "towns_industries/YRD_1950.lua").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    names = []
    for p in industries:
        name = json.dumps(p["name"], ensure_ascii=False)
        key = p["key"]
        names.append(
            f'{{ name = {name}, x = {p["x"]:.2f}, y = {p["y"]:.2f}, '
            f'fileName = "::/industries/{key}/{key}.con" }}'
        )
    command = (REPO / "scripts/restore_names.lua").read_text(encoding="utf-8")
    command = command.replace("{{INDUSTRIES}}", ", ".join(names))
    (OUT / "docs/恢复产业名称.txt").write_text(
        " ".join(line.strip() for line in command.splitlines()) + "\n",
        encoding="utf-8",
    )


def csvs():
    for name, items in [("城市", towns), ("产业", industries)]:
        fieldnames = list(items[0])
        with (OUT / f"docs/{name}坐标与参数.csv").open(
            "w", encoding="utf-8-sig", newline=""
        ) as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(items)


def preview(height, water, biomes, industrial=False):
    size = 1700
    h = np.asarray(
        Image.fromarray(height).resize((size, size), Image.Resampling.BILINEAR)
    )
    b = np.asarray(
        Image.fromarray(biomes).resize((size, size), Image.Resampling.NEAREST)
    )
    w = (
        np.asarray(
            Image.fromarray(water.astype(np.uint8) * 255).resize(
                (size, size), Image.Resampling.NEAREST
            )
        )
        > 0
    )
    rgb = np.zeros((size, size, 3), dtype=np.float32) + [176, 194, 134]
    rgb[b == 77] = [97, 139, 101]
    rgb[b == 128] = [145, 179, 148]
    gy, gx = np.gradient(h)
    shading = np.clip(0.92 + (-gx - gy) * 0.12, 0.55, 1.2)
    rgb *= shading[:, :, None]
    rgb[w] = [111, 162, 186]
    base = Image.fromarray(np.uint8(np.clip(rgb, 0, 255)))
    canvas = Image.new("RGB", (1860, 1990), "#f4f4ef")
    canvas.paste(base, (80, 140))
    draw = ImageDraw.Draw(canvas)
    fontpath = str(FONT_PATH)
    title = ImageFont.truetype(fontpath, 38)
    font = ImageFont.truetype(fontpath, 20)
    small = ImageFont.truetype(fontpath, 18)
    draw.text(
        (80, 38),
        CFG["title"] + " · " + ("产业布局" if industrial else "地形与小城开局"),
        font=title,
        fill="#203c3e",
    )
    draw.text(
        (80, 94),
        f"Gigantomaniac 1:1  |  {GAME_SIDE / 1000:.3f} km × {GAME_SIDE / 1000:.3f} km  |  顺时针旋转 {CFG.get('rotation_deg', 0):g}°  |  现实范围约 {REAL_SIDE / 1000:.0f} km × {REAL_SIDE / 1000:.0f} km",
        font=font,
        fill="#485b5d",
    )
    for i, p in enumerate(towns):
        x = 80 + (p["x"] / GAME_SIDE + 0.5) * (size - 1)
        y = 140 + (0.5 - p["y"] / GAME_SIDE) * (size - 1)
        draw.ellipse(
            (x - 5, y - 5, x + 5, y + 5), fill="#9b3433", outline="white", width=2
        )
        offset = (
            -25 if p["name"] in ["常州", "扬州", "无锡", "马鞍山矿区", "嘉兴"] else 8
        )
        text = p["name"]
        if not industrial and p["name"] in {"上海", "南京", "杭州"}:
            text += f" ≈{p['initial_people_estimated']}人"
        draw.text(
            (x + 9, y + offset),
            text,
            font=font,
            fill="#23383b",
            stroke_width=2,
            stroke_fill="#f4f4ef",
        )
    if industrial:
        colors = {
            "farm": "#c3931a",
            "livestock_farm": "#c3931a",
            "cotton_farm": "#c3931a",
            "fishing_grounds": "#1e618f",
            "oil_platform": "#1e618f",
            "forest": "#255c37",
            "saw_mill": "#255c37",
        }
        for p in industries:
            x = 80 + (p["x"] / GAME_SIDE + 0.5) * (size - 1)
            y = 140 + (0.5 - p["y"] / GAME_SIDE) * (size - 1)
            color = colors.get(p["key"], "#714270")
            draw.rectangle((x - 5, y - 5, x + 5, y + 5), fill=color, outline="white")
            draw.text(
                (x + 7, y - 15),
                p["id"],
                font=small,
                fill=color,
                stroke_width=2,
                stroke_fill="#f4f4ef",
            )
    for name, lon, lat in [
        ("太湖", 120.13, 31.25),
        ("长江", 119.90, 32.02),
        ("杭州湾", 121.36, 30.54),
        ("天目山", 119.43, 30.35),
        ("近海", 121.87, 30.83),
        ("石臼湖", 118.85, 31.54),
        ("舟山群岛", 122.20, 30.25),
    ]:
        x, y = xy(lon, lat)
        draw.text(
            (80 + (x / GAME_SIDE + 0.5) * size, 140 + (0.5 - y / GAME_SIDE) * size),
            name,
            font=font,
            fill="#326f81",
            stroke_width=2,
            stroke_fill="#dfe9e2",
        )
    angle = math.radians(CFG.get("rotation_deg", 0))
    tip = (1700 + math.sin(angle) * 70, 265 - math.cos(angle) * 70)
    draw.line([(1700, 265), tip], fill="#203c3e", width=4)
    draw.regular_polygon(
        (tip[0], tip[1], 9), 3, rotation=-CFG.get("rotation_deg", 0), fill="#203c3e"
    )
    draw.text((tip[0] - 12, tip[1] - 40), "N", font=title, fill="#203c3e")
    y = 1880
    draw.text(
        (80, y),
        f"{len(towns)} 座小城 · {len(industries)} 个产业点 · 山地压缩至约 {height.max():.0f} m · 低地保留缓坡和建设空间",
        font=font,
        fill="#203c3e",
    )
    draw.text(
        (80, y + 34),
        "DEM: Mapzen Terrain Tiles  |  海岸/湖泊: Natural Earth  |  自然河流: OpenStreetMap contributors",
        font=small,
        fill="#485b5d",
    )
    draw.text(
        (80, y + 65),
        "植被为地形驱动的设计分布；人数为预计值。本图为离线预览，实际导入结果见包内游戏验收记录。",
        font=small,
        fill="#485b5d",
    )
    canvas.save(OUT / ("产业布局预览.png" if industrial else "地图预览.png"))


def validate(height, water, biomes, real_dem, lakes):
    failures = []
    for p in towns + industries:
        rr, cc = p["pixel_row"], p["pixel_col"]
        if bool(water[rr, cc]) != p.get("on_water", False):
            failures.append(p["name"] + ": land/water mismatch")
        if abs(p["x"]) >= GAME_SIDE / 2 or abs(p["y"]) >= GAME_SIDE / 2:
            failures.append(p["name"] + ": outside map")
    for i, p in enumerate(towns + industries):
        for q in (towns + industries)[i + 1 :]:
            if math.hypot(p["x"] - q["x"], p["y"] - q["y"]) < 380:
                failures.append(
                    p["name"] + " / " + q["name"] + ": insufficient spacing"
                )
    png = OUT / "heightmaps/YRD_1950_7169.png"
    data = png.read_bytes()[:29]
    width, h, depth, color = struct.unpack(">IIBB", data[16:26])
    if (width, h, depth, color) != (FINAL, FINAL, 16, 0):
        failures.append("PNG dimensions/encoding incorrect")
    source_tags = set(p["key"] for p in industries)
    # Every initial cargo demand must have a producer; only boosters may be optional.
    produces = {
        "farm": ["vegetables", "grain"],
        "livestock_farm": ["meat", "wool"],
        "forest": ["logs"],
        "saw_mill": ["planks", "sawdust"],
        "clay_pit": ["clay"],
        "bricks_works": ["bricks"],
        "sand_pit": ["sand"],
        "glass_works": ["glass"],
        "cotton_farm": ["wool"],
        "weaving_mill": ["fabric"],
        "textile_factory": ["clothes"],
        "coal_mine": ["coal"],
        "iron_ore_mine": ["iron_ore"],
        "steel_mill": ["steel", "sheet_metal"],
        "oil_platform": ["crude_oil"],
        "oil_refinery": ["fuel", "chemicals", "fertilizer"],
        "chemical_plant": ["dyes", "plastic"],
        "machine_factory": ["machines"],
        "tool_factory": ["tools"],
        "furniture_factory": ["furniture"],
        "brewery": ["beverages"],
        "food_factory": ["tinned_food"],
        "fishing_grounds": ["fish"],
    }
    required = {
        "livestock_farm": ["grain"],
        "saw_mill": ["logs"],
        "bricks_works": ["clay"],
        "glass_works": ["sand"],
        "weaving_mill": ["wool"],
        "textile_factory": ["fabric", "dyes"],
        "steel_mill": ["coal", "iron_ore"],
        "oil_refinery": ["crude_oil"],
        "chemical_plant": ["chemicals"],
        "machine_factory": ["steel", "plastic"],
        "tool_factory": ["planks", "plastic"],
        "furniture_factory": ["planks", "glass"],
        "brewery": ["grain", "glass"],
        "food_factory": ["fish", "sheet_metal"],
    }
    supplied = {cargo for key in source_tags for cargo in produces[key]}
    for p in towns:
        for cargo in [p["com"], p["ind"]]:
            if cargo not in supplied:
                failures.append(p["name"] + ": missing " + cargo)
    for key in source_tags:
        for cargo in required.get(key, []):
            if cargo not in supplied:
                failures.append(key + ": missing input " + cargo)
    boosters = {
        "forest": ["machines"],
        "iron_ore_mine": ["machines"],
        "farm": ["fertilizer"],
        "cotton_farm": ["fertilizer"],
        "coal_mine": ["tools"],
        "clay_pit": ["tools"],
        "sand_pit": ["tools"],
        "fishing_grounds": ["tools"],
        "oil_platform": ["tools"],
    }
    demand = {p[c] for p in towns for c in ("com", "ind")}

    def reaches_town(key, visited):
        if key in visited:
            return False
        visited = visited | {key}
        for cargo in produces[key]:
            if cargo in demand:
                return True
            for consumer in source_tags:
                if cargo in required.get(consumer, []) + boosters.get(consumer, []):
                    if reaches_town(consumer, visited):
                        return True
        return False

    for key in source_tags:
        if not reaches_town(key, set()):
            failures.append(key + ": no downstream city demand")
    channels, count = label(water)
    ocean_row, ocean_col = pixels(121.89, 30.80)[::-1]
    ocean_component = int(channels[round(ocean_row), round(ocean_col)])
    if ocean_component == 0:
        failures.append("Ocean reference point is not water")
    navigation_samples = []
    for name, nominal_width, points in routes:
        for lon, lat in points:
            col, row = pixels(lon, lat)
            if not (0 <= col <= N - 1 and 0 <= row <= N - 1):
                continue
            r, c = round(row), round(col)
            component = int(channels[r, c])
            central_depth = -float(height[r, c])
            radius_m = float(distance[r, c]) * GAME_SIDE / (N - 1)
            navigation_samples.append(
                dict(
                    route=name,
                    lon=lon,
                    lat=lat,
                    component=component,
                    central_depth_m=central_depth,
                    water_radius_m=radius_m,
                )
            )
            if central_depth < 2:
                failures.append(name + ": dry navigation sample")
            if radius_m < 4:
                failures.append(name + ": collapsed channel sample")
    # Test the encoded import surface, with 16 m of bank clearance, on sea alone.
    # Inland canals cannot hide a disconnected bay or island sea in this check.
    sea_heights = np.asarray(Image.open(png), dtype=np.float32)
    sea_heights *= (MAX_HEIGHT - MIN_HEIGHT) / 65535
    sea_heights += MIN_HEIGHT
    pixel_m = GAME_SIDE / (FINAL - 1)
    final_sea = np.asarray(Image.open(OUT / "docs/参考蒙版/YRD_sea.png")) > 0
    sea_radius = distance_transform_edt(final_sea & (sea_heights < WATER_LEVEL))
    sea_channels, _ = label(sea_radius * pixel_m >= 16)
    sea_samples = []
    sea_component = None
    for name, lon, lat in json.loads(
        (REPO / "data/sea-navigation.json").read_text(encoding="utf-8")
    ):
        col, row = pixels(lon, lat)
        if not (0 <= col <= N - 1 and 0 <= row <= N - 1):
            failures.append(name + ": sea checkpoint outside map")
            continue
        r, c = round(row * (FINAL - 1) / (N - 1)), round(col * (FINAL - 1) / (N - 1))
        component = int(sea_channels[r, c])
        if sea_component is None:
            sea_component = component
        sea_samples.append(
            dict(
                name=name,
                lon=lon,
                lat=lat,
                component=component,
                depth_m=-float(sea_heights[r, c]),
                sea_clearance_m=float(sea_radius[r, c]) * pixel_m,
            )
        )
        if component == 0 or component != sea_component:
            failures.append(
                name + ": sea disconnected or less than 16 m bank clearance"
            )
    for p in industries:
        if p["on_water"] and sea[p["pixel_row"], p["pixel_col"]]:
            r = round(p["pixel_row"] * (FINAL - 1) / (N - 1))
            c = round(p["pixel_col"] * (FINAL - 1) / (N - 1))
            if int(sea_channels[r, c]) != sea_component:
                failures.append(p["name"] + ": disconnected sea industry")
    report = dict(
        status="offline checks passed" if not failures else "failed",
        failed_checks=failures,
        png=dict(width=width, height=h, bit_depth=depth, color_type=color),
        towns=len(towns),
        industries=len(industries),
        game_extent_m=[GAME_SIDE, GAME_SIDE],
        real_extent_m=[REAL_SIDE, REAL_SIDE],
        rotation_deg=CFG.get("rotation_deg", 0),
        map_corners_lon_lat=corners(CFG),
        horizontal_compression=SCALE,
        height_range_m=[float(height.min()), float(height.max())],
        real_dem_height_range_m=[float(real_dem.min()), float(real_dem.max())],
        water_fraction=float(water.mean()),
        forest_biome_land_fraction=float(
            ((biomes == 77) & ~water).sum() / (~water).sum()
        ),
        initial_people_estimated=sum(p["initial_people_estimated"] for p in towns),
        city_factors_range=[
            min(p["factor"] for p in towns),
            max(p["factor"] for p in towns),
        ],
        lakes_and_reservoirs=lakes,
        game_import_tested=False,
        all_industries_have_downstream_city_demand=not any(
            "downstream" in f for f in failures
        ),
        maximum_placement_shift_game_m=max(
            p["position_shift_m"] for p in towns + industries
        ),
        surface_navigation_connectivity="river samples checked for depth; inland fisheries may occupy independent lakes; final PNG sea and offshore industries checked with 16 m bank clearance; ship pathfinding untested",
        navigation_samples=navigation_samples,
        ocean_component=ocean_component,
        sea_connectivity=dict(
            surface="decoded final PNG, sea-only mask",
            minimum_bank_clearance_m=16,
            status="passed" if not any("sea" in f for f in failures) else "failed",
            samples=sea_samples,
        ),
        on_water_industries=[
            dict(
                id=p["id"],
                name=p["name"],
                water_component=int(channels[p["pixel_row"], p["pixel_col"]]),
            )
            for p in industries
            if p["on_water"]
        ],
        sources_date="2026-10-14",
        version=CFG["version"],
    )
    (OUT / "docs/离线检查.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"{report['status']}: {len(towns)} towns, {len(industries)} industries, "
        f"{len(navigation_samples)} river samples; failures={failures}",
        flush=True,
    )
    if failures:
        raise RuntimeError("Validation failed")


for folder in ["heightmaps", "biomes", "towns_industries", "docs"]:
    (OUT / folder).mkdir(parents=True, exist_ok=True)
for marker in ["manifest.json", "docs/离线检查.json", "SHA256SUMS.txt"]:
    (OUT / marker).unlink(missing_ok=True)
for file in ["import-guide.md", "methodology.md"]:
    shutil.copyfile(
        REPO / "docs" / file,
        OUT
        / ("使用说明.md" if file == "import-guide.md" else "docs/来源与制作口径.md"),
    )
shutil.copyfile(ARGS.config, OUT / "docs/map-config.json")
shutil.copyfile(REPO / "data/waterways.geojson", OUT / "docs/水系中心线.geojson")
print("Read DEM", flush=True)
real_dem = read_dem()
print("Rasterize water", flush=True)
water, sea, rivers, lakes, routes = water_masks()
# Preserve relief but compress vertically. Banks ease into a flat global water plane.
height = np.maximum(
    3.2, 3.2 + np.maximum(real_dem - 5, 0) * CFG["height_factor"]
).astype(np.float32)
distance = distance_transform_edt(water)
bank_blend = np.minimum(distance_transform_edt(~water) * (GAME_SIDE / (N - 1)) / 48, 1)
height = 3.2 + (height - 3.2) * bank_blend.astype(np.float32)
depth = np.minimum(12, 4 + distance * 1.25).astype(np.float32)
height[water] = -depth[water]
height = gaussian_filter(height, 0.65)
height[water] = np.minimum(height[water], -2.5)
height[~water] = np.maximum(height[~water], 1.8)
assert height.max() < MAX_HEIGHT, "Terrain exceeds PNG encoding range"
placements = []
print("Place towns/industries", flush=True)
for p in towns:
    settle(p, height, water, placements, 140, 500)
for p in industries:
    radius = (
        80
        if p["on_water"]
        else (
            300
            if p["key"] == "forest"
            else (155 if p["key"] in ["farm", "cotton_farm", "livestock_farm"] else 100)
        )
    )
    settle(p, height, water, placements, radius, 350 if p["on_water"] else 500)
print("Biomes and PNG", flush=True)
biomes = biome_map(real_dem, water, placements)
full = np.asarray(
    Image.fromarray(height).resize((FINAL, FINAL), Image.Resampling.BILINEAR)
)
normalized = np.rint(
    np.clip((full - MIN_HEIGHT) / (MAX_HEIGHT - MIN_HEIGHT), 0, 1) * 65535
).astype(np.uint16)
Image.fromarray(normalized).save(OUT / "heightmaps/YRD_1950_7169.png")
for name, array in [
    ("biomes", biomes),
    ("mountains", (real_dem > 650).astype(np.uint8) * 255),
    ("rivers", rivers.astype(np.uint8) * 255),
    ("sea", sea.astype(np.uint8) * 255),
]:
    folder = OUT / ("biomes" if name == "biomes" else "docs/参考蒙版")
    folder.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array).resize((FINAL, FINAL), Image.Resampling.NEAREST).save(
        folder / f"YRD_{name}.png"
    )
export_lua()
csvs()
preview(height, water, biomes)
preview(height, water, biomes, True)
np.save(CACHE / "game_heights.npy", height)
np.save(CACHE / "water_mask.npy", water)
(OUT / "docs/布局数据.json").write_text(
    json.dumps(
        dict(towns=towns, industries=industries, routes=routes),
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
validate(height, water, biomes, real_dem, lakes)

report = json.loads((OUT / "docs/离线检查.json").read_text(encoding="utf-8"))
dem_manifest = json.loads((CACHE / "dem_manifest.json").read_text(encoding="utf-8"))
shutil.copyfile(CACHE / "dem_manifest.json", OUT / "docs/源数据清单.json")
values = {
    "TOWNS": len(towns),
    "INDUSTRIES": len(industries),
    "EST_POP": report["initial_people_estimated"],
    "REAL_SIDE_KM": round(REAL_SIDE / 1000),
    "SCALE": f"{SCALE:.2f}",
    "MAX_TERRAIN": f"{float(height.max()):.0f}",
    "FOREST_PERCENT": round(report["forest_biome_land_fraction"] * 100),
    "TILE_COUNT": len(dem_manifest["tiles"]),
    "ZOOM": CFG["dem_zoom"],
    "CENTER": f"东经 {CLON}°、北纬 {CLAT}°",
    "BBOX": f"东经 {WEST:.4f}°—{EAST:.4f}°、北纬 {SOUTH:.4f}°—{NORTH:.4f}°",
    "SOURCE_SPACING": f"{156543.033928 * math.cos(math.radians(CLAT)) / 2 ** CFG['dem_zoom']:.1f}",
    "REAL_GRID_SPACING": f"{REAL_SIDE / (FINAL - 1):.1f}",
    "ROTATION": CFG.get("rotation_deg", 0),
    "CORNERS": "；".join(f"{lon:.4f}°E, {lat:.4f}°N" for lon, lat in corners(CFG)),
}
for source, destination in [
    ("import-guide.md", "使用说明.md"),
    ("methodology.md", "docs/来源与制作口径.md"),
    ("game-validation.md", "docs/游戏验收.md"),
]:
    body = (REPO / "docs" / source).read_text(encoding="utf-8")
    for key, value in values.items():
        body = body.replace("{{" + key + "}}", str(value))
    assert "{{" not in body, "Unresolved document parameter"
    (OUT / destination).write_text(body, encoding="utf-8")
manifest = dict(
    title=CFG["title"],
    version=CFG["version"],
    game="Transport Fever 3",
    platform="Windows",
    start_year=CFG["start_year"],
    map_size="Gigantomaniac",
    aspect_ratio="1:1",
    game_size_m=[GAME_SIDE, GAME_SIDE],
    heightmap_pixels=[FINAL, FINAL],
    heightmap_bit_depth=16,
    import_black_height_m=MIN_HEIGHT,
    import_white_height_m=MAX_HEIGHT,
    water_level_m=WATER_LEVEL,
    reference_bbox_lon_lat=bounds(CFG),
    rotation_deg=CFG.get("rotation_deg", 0),
    map_corners_lon_lat=corners(CFG),
    real_side_m=REAL_SIDE,
    towns=len(towns),
    industries=len(industries),
    requires_mods=False,
    required_editor_settings={"nameList": CFG["nameList"], "language": CFG["language"]},
    game_import_tested=False,
    saved_game_map_included=False,
)
(OUT / "manifest.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
lookup = {p["id"]: p for p in industries} | {p["name"]: p for p in towns}
links = [
    ("A04", "杭州"),
    ("A07", "句容"),
    ("B01", "B02"),
    ("L01", "L04"),
    ("W01", "湖州"),
    ("H01", "H03"),
    ("H02", "H03"),
    ("H03", "H04"),
    ("T01", "T02"),
    ("T02", "T03"),
    ("O01", "O02"),
    ("O02", "O03"),
    ("F01", "杭州"),
    ("F03", "富阳"),
]
rows = []
for a, b in links:
    p, q = lookup[a], lookup[b]
    rows.append(
        {
            "起点": p["name"],
            "终点": q["name"],
            "直线距离_游戏km": round(
                math.hypot(p["x"] - q["x"], p["y"] - q["y"]) / 1000, 2
            ),
        }
    )
with (OUT / "docs/推荐链条距离.csv").open(
    "w", encoding="utf-8-sig", newline=""
) as file:
    writer = csv.DictWriter(file, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
print(f"Built {OUT}", flush=True)
