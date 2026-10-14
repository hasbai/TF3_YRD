"""Package a validated TF3 import map and record its SHA256."""

import hashlib
import json
import zipfile
from common import options, load_config, bounds, corners


def main():
    args = options(__doc__)
    cfg = load_config(args.config)
    root = args.output
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    exported_config = json.loads(
        (root / "docs/map-config.json").read_text(encoding="utf-8")
    )
    assert exported_config == cfg, "Exported map/config mismatch: rebuild first"
    assert manifest["version"] == cfg["version"]
    assert manifest["reference_bbox_lon_lat"] == bounds(cfg)
    assert manifest["rotation_deg"] == cfg.get("rotation_deg", 0)
    assert manifest["map_corners_lon_lat"] == corners(cfg)
    assert manifest["heightmap_pixels"] == [cfg["resolution"], cfg["resolution"]]
    assert manifest["game_size_m"] == [cfg["game_side_m"], cfg["game_side_m"]]
    report = json.loads((root / "docs/离线检查.json").read_text(encoding="utf-8"))
    assert report["status"] == "offline checks passed", report["failed_checks"]
    assert report["version"] == cfg["version"]
    assert report["towns"] == manifest["towns"]
    assert report["industries"] == manifest["industries"]
    checksums = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            checksums.append(
                hashlib.sha256(path.read_bytes()).hexdigest()
                + "  "
                + path.relative_to(root).as_posix()
            )
    (root / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    target = root.parent / f"TF3_YRD_v{cfg['version']}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            entry = zipfile.ZipInfo(
                "YRD_1950/" + path.relative_to(root).as_posix(), (2026, 10, 14, 0, 0, 0)
            )
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, path.read_bytes())
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".zip.sha256").write_text(
        digest + "  " + target.name + "\n", encoding="utf-8"
    )
    print(f"{target}: {target.stat().st_size / 1024**2:.1f} MiB\nSHA256 {digest}")


if __name__ == "__main__":
    main()
