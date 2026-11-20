# Demo map data

`DEMO_synthetic_flood_extent.geojson` is **synthetic**: one hand-drawn polygon around the demo
disaster zone in `.env` (22.57 N, 88.36 E). It is **not satellite data**. It exists only so the
satellite check and the dashboard's flood overlay can be shown before real data is loaded.

To use it: `FLOOD_MAP_FILES=data/demo/DEMO_synthetic_flood_extent.geojson` in `.env`.

For a real demo, replace it with a real flood-extent file and keep the source in the file name:
- **Copernicus EMS Rapid Mapping**: https://mapping.emergency.copernicus.eu/activations. Pick an
  Indian flood activation (EMSR...), download the vector package of the "delineation" or
  "observed flood extent" product, and point `FLOOD_MAP_FILES` at its `.shp` or GeoJSON.
- **ISRO Bhuvan / NRSC (NDEM)**: flood inundation layers. Downloading needs a login or a
  government data request.

Building footprints (`BUILDING_FILES`): a Google Open Buildings CSV or an OpenStreetMap building
export (GeoJSON) for the same district.
