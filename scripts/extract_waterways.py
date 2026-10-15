"""Extract named regional waterways from the cached Geofabrik OSM files."""

import hashlib
import json

import osmium

from common import REPO, bounds, load_config, options


def main():
    args = options(__doc__)
    cfg = load_config(args.config)
    west, south, east, north = bounds(cfg)
    features = {}
    names = {
        "长江", "长江南支", "长江北支", "长江南港", "长江北港", "长江南槽", "长江北槽",
        "钱塘江", "富春江", "新安江", "曹娥江", "甬江", "姚江", "姚江故道", "奉化江",
        "黄浦江", "吴淞江", "苏州河",
    }

    class Waterways(osmium.SimpleHandler):
        def way(self, way):
            waterway = way.tags.get("waterway")
            name = way.tags.get("name:zh", way.tags.get("name", ""))
            if waterway != "river" or name not in names:
                return
            points = [[node.lon, node.lat] for node in way.nodes]
            if not any(west <= x <= east and south <= y <= north for x, y in points):
                return
            width = 40
            if name in {"长江", "长江南支", "长江北支", "长江南港", "长江北港", "长江南槽", "长江北槽"}:
                width = 160
            elif name == "钱塘江":
                width = 100
            elif name == "富春江":
                width = 64
            elif name == "黄浦江":
                width = 48
            features[way.id] = {
                "type": "Feature",
                "properties": {
                    "name": name,
                    "osm_way_id": way.id,
                    "width_game_m": width,
                    "waterway": waterway,
                },
                "geometry": {"type": "LineString", "coordinates": points},
            }

    sources = []
    for region in cfg["waterway_regions"]:
        path = args.cache / "osm" / f"{region}.osm.pbf"
        print(f"Extract {region}", flush=True)
        Waterways().apply_file(path, locations=True, idx="sparse_mem_array")
        sources.append(
            {
                "region": region,
                "url": f"https://download.geofabrik.de/asia/china/{region}-latest.osm.pbf",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    result = {
        "type": "FeatureCollection",
        "attribution": "© OpenStreetMap contributors, ODbL 1.0; Geofabrik extracts",
        "sources": sources,
        "features": [features[key] for key in sorted(features)],
    }
    target = REPO / "data/waterways.geojson"
    target.write_text(json.dumps(result, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(features)} OSM ways -> {target}")


if __name__ == "__main__":
    main()
