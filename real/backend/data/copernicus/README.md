# Real satellite data: Copernicus EMS

These files are **real** satellite-derived products from the **Copernicus Emergency Management
Service (CEMS) Rapid Mapping**, converted to WGS84 GeoJSON with `scripts/convert_cems.py`.

**Source / credit:** © European Union, Copernicus Emergency Management Service.
https://mapping.emergency.copernicus.eu. CEMS gives "free, full and open access", including
reproduction and adaptation, on condition that the source is cited whenever the data is shown or
shared. Keep this credit on any map, slide or screenshot that uses them. Data is provided "as is",
without warranty.

| File | Activation | What it is | Features |
|---|---|---|---|
| `EMSR104_andhra_flood_2014-10-12.geojson` | [EMSR104](https://mapping.emergency.copernicus.eu/activations/EMSR104/): flood in Andhra Pradesh after Cyclone Hudhud (Oct 2014) | **Flooded areas** around Dwaraka Nagar (Visakhapatnam) and Thagarapuvalasa, from satellite images of 12 Oct 2014 | 313 polygons |
| `EMSR357_puri_flood_2019.geojson` | [EMSR357](https://mapping.emergency.copernicus.eu/activations/EMSR357/): Cyclone Fani, Odisha (May 2019) | **Flooded areas and flood traces** in Puri | 354 polygons |
| `EMSR357_puri_building_damage_2019.geojson` | EMSR357 | **Every building graded from satellite images**: 1,333 Destroyed, 7,751 Damaged, 693 Possibly damaged | 9,777 points |

Use them in `Member-3/.env`:
```
FLOOD_MAP_FILES=data/copernicus/EMSR104_andhra_flood_2014-10-12.geojson,data/copernicus/EMSR357_puri_flood_2019.geojson
BUILDING_FILES=data/copernicus/EMSR357_puri_building_damage_2019.geojson
```
For a demo in Puri, also set the disaster zone and date, for example `DISASTER_ZONE_LAT=19.81`,
`DISASTER_ZONE_LON=85.83`, `DISASTER_ZONE_RADIUS_KM=50`, `DISASTER_START_DATE=2019-05-01`.

Notes:
- The building file lists only **graded** buildings (damaged ones). Undamaged buildings are not in
  it, so for Puri a "no building mapped" result can simply mean "not damaged", not "no house".
- Flood maps show the water when the satellite passed. Wind-damaged buildings can be outside them;
  the service does not flag those when satellite grading shows damage.
- Original vector packages: `EMSR104_04THAGARAPUVALASA_DELINEATION_OVERVIEW_v1_vector.zip`,
  `EMSR104_03DWARAKANAGAR_DELINEATION_OVERVIEW_v1_vector.zip`,
  `EMSR357_AOI08_GRA_PRODUCT_r1_RTP01_v2_vector.zip` (cems-mapping-website S3 bucket).
