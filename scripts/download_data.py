"""Download and verify the DEM tiles required by config/map.json."""

import concurrent.futures
import hashlib
import json
import math
import time
import urllib.request
from PIL import Image
from common import options, load_config, bounds


def tile(lon, lat, zoom):
    n = 2**zoom
    return (
        (lon + 180) / 360 * n,
        (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n,
    )


def fetch(url, path):
    if path.exists():
        return
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                body = response.read()
            temporary = path.with_suffix(path.suffix + ".part")
            temporary.write_bytes(body)
            temporary.replace(path)
            return
        except OSError:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


def main():
    args = options(__doc__)
    cfg = load_config(args.config)
    cache = args.cache
    cache.mkdir(parents=True, exist_ok=True)
    out = cache / "dem"
    out.mkdir(exist_ok=True)
    zoom = cfg["dem_zoom"]
    bbox = bounds(cfg)
    west, south, east, north = bbox
    x0, y0 = tile(west, north, zoom)
    x1, y1 = tile(east, south, zoom)
    jobs = [
        (x, y)
        for x in range(math.floor(x0), math.floor(x1) + 1)
        for y in range(math.floor(y0), math.floor(y1) + 1)
    ]
    print(f"DEM zoom {zoom}: {len(jobs)} tiles", flush=True)

    def download(job):
        x, y = job
        p = out / f"{zoom}_{x}_{y}.png"
        fetch(
            f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{zoom}/{x}/{y}.png",
            p,
        )
        with Image.open(p) as image:
            assert image.size == (256, 256) and image.mode == "RGB", p
            image.verify()
        return p.name, hashlib.sha256(p.read_bytes()).hexdigest()

    hashes = {}
    errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        futures = {pool.submit(download, j): j for j in jobs}
        for i, f in enumerate(concurrent.futures.as_completed(futures), 1):
            try:
                name, digest = f.result()
                hashes[name] = digest
            except Exception as error:
                errors.append((futures[f], str(error)))
            if i % 100 == 0 or i == len(jobs):
                print(f"{i}/{len(jobs)}; failed={len(errors)}", flush=True)
    if errors:
        raise RuntimeError(errors)
    for name in ["ne_10m_land", "ne_10m_lakes", "ne_10m_rivers_lake_centerlines"]:
        fetch(
            f"https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{cfg['natural_earth_revision']}/geojson/{name}.geojson",
            cache / f"{name}.geojson",
        )
        hashes[name + ".geojson"] = hashlib.sha256(
            (cache / f"{name}.geojson").read_bytes()
        ).hexdigest()
    manifest = {
        "zoom": zoom,
        "bbox": bbox,
        "center": [cfg["center_lat"], cfg["center_lon"]],
        "real_side_m": cfg["real_side_m"],
        "tiles": jobs,
        "sha256": dict(sorted(hashes.items())),
    }
    (cache / "dem_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print("Download complete; hashes recorded.", flush=True)


if __name__ == "__main__":
    main()
