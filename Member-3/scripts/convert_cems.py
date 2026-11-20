"""Convert a Copernicus EMS (or other) shapefile into a small WGS84 GeoJSON for this service.

Copernicus EMS vector packages come as shapefiles, sometimes in metres (UTM). This converts
them to longitude/latitude, keeps only useful fields, and records the source, as the
Copernicus terms ask ("inform the recipients of the source").

From Member-3/:
    python scripts/convert_cems.py IN.shp OUT.geojson --source "Copernicus EMS EMSR104 (2014-10-12)"
        [--keep interpret,src_date] [--where notation=Flooded area]
"""
import argparse
import json
import sys
from pathlib import Path

from shapely.geometry import mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.geodata import _read_geometries  # noqa: E402


def rounded(obj, nd=6):
    if isinstance(obj, float):
        return round(obj, nd)
    if isinstance(obj, (list, tuple)):
        return [rounded(x, nd) for x in obj]
    if isinstance(obj, dict):
        return {k: rounded(v, nd) for k, v in obj.items()}
    return obj


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", help="input .shp files, then the output .geojson last")
    ap.add_argument("--source", required=True, help="credit line, e.g. 'Copernicus EMS EMSR357'")
    ap.add_argument("--keep", default="", help="comma-separated fields to keep")
    ap.add_argument("--where", default="", help="only features with FIELD=VALUE")
    args = ap.parse_args()
    *ins, out = args.inputs
    keep = [k for k in args.keep.split(",") if k]
    field, _, value = args.where.partition("=")

    feats = []
    for path in ins:
        for geom, props in _read_geometries(Path(path)):
            if field and str(props.get(field)) != value:
                continue
            p = {k: props[k] if isinstance(props[k], (int, float, str, type(None))) else str(props[k])
                 for k in keep if k in props}   # dates etc. -> text
            p["source"] = args.source
            feats.append({"type": "Feature", "geometry": rounded(mapping(geom)), "properties": p})
    fc = {"type": "FeatureCollection", "source": args.source,
          "license": "Copernicus Emergency Management Service: free, full and open access; cite the source",
          "features": feats}
    Path(out).write_text(json.dumps(fc, separators=(",", ":")), encoding="utf-8")
    print(f"{out}: {len(feats)} features, {Path(out).stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
