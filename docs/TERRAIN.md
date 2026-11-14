# Task 3 — Lunar terrain data (deliverable)

Terrain data for the three Phase 1 mission candidates, obtained from NASA and
measured from the files themselves. The deliverable is:

- three **5 m/pixel LOLA digital elevation models** (one per candidate, 16 km ×
  16 km each), downloaded from NASA PGDA and verified by checksum;
- one **80 m/pixel wide polar DEM** (`LDEM_80S_80MPP_ADJ`, 7600 × 7600 px, 80°S
  to the pole) that carries the masks from the end of each site DEM to 150 km;
- committed descriptions of both: `data/reference/site_terrain.json`
  (`schema: lunanav.site_terrain.v1`) and `data/reference/wide_dem.json`
  (`schema: lunanav.wide_terrain.v1`);
- the skyline obstruction angle per azimuth out to the edge of each DEM, and
  the two-tier 360-point horizon masks built from them (Phase 2 Task 6).

This is the data layer. The masks built from these DEMs are in
`data/scientific/horizon_masks/` and described in
[docs/DATA_ACCESS.md](DATA_ACCESS.md); nothing here certifies a landing site.

## Per-site result

Site coordinates and elevations are the Phase 1 records in
`data/demo/sites.json` and `docs/SITES.md`. "DEM pixel" is the single 5 m pixel
containing the coordinate; the catalogue elevation is the median of the
125 m × 125 m window around it, so the two differ slightly by design.

| Site | DEM | Catalogue elevation | DEM pixel | Terrain within radius | Skyline min … max (0 m eye) | Max obstruction (0 m eye) | Usable radius |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `shackleton-rim` (−89.78°, −155.73°) | Site04 | 1,734.05 m | 1,728.34 m | −2,001.5 … +1,739.1 m | +3.08° … +12.66° | **12.66° at 229° az** | **6.258 km** |
| `connecting-ridge` (−89.45°, −137.31°) | Site01 | 1,955.23 m | 1,954.85 m | +154.7 … +1,959.5 m | −1.72° … +10.63° | **10.63° at 160° az** | **7.692 km** |
| `de-gerlache-rim` (−88.67°, −68.10°) | Site11 | 1,808.10 m | 1,808.37 m | −511.1 … +1,816.0 m | −2.53° … +5.95° | **5.95° at 265° az** | **7.579 km** |

Read the obstruction column as a fact about the 6–8 km of ground in the file,
measured from a ground-level observer, not about the whole skyline. The Phase 3
masks sample the same terrain from the 2 m eye the Sun/Earth track uses, which
lowers near-field angles (by `atan(2 m / distance)`); their maxima are 9.43°,
2.85° and 1.28°. Each mask also covers 8–150 km at 80 m/pixel; the far tier's
own maxima are +1.06°, −0.85° and −0.22°, all below the near skyline, so the
distant massifs do not out-top the local rim at these three points. At Shackleton the crest of the rim itself stands
12.7° above the landing point to the south-west; the connecting ridge is blocked
to 10.6° toward 160° (the ridge falls away north, so the horizon there is
negative, i.e. below the tangent plane). For comparison, the Sun never rises
more than ~1.7° at these sites in the mission windows (Task 2 series), so local
terrain of this size decides illumination far more than the geometric horizon
does.

## Datasets

| Dataset | Resolution | Coverage | Frame / datum | Source | Use here |
| --- | --- | --- | --- | --- | --- |
| LOLA 5 m/pix south-pole site DEMs, `*_final_adj_5mpp_surf.tif` | 5 m/pixel, 3200 × 3200 | 16 km × 16 km centred on each PGDA site point | Moon ME, south polar stereographic (sphere 1737.4 km); heights in metres above the 1737.4 km sphere | NASA PGDA [products/78](https://pgda.gsfc.nasa.gov/products/78), data at [LOLA_5mpp](https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/); Barker et al. 2021 | **Primary DEM** — elevations and obstruction angles |
| Same sites, `*_slp.tif` (slope, degrees) and `*_toterr.tif` (RMS height error, m) | 5 m/pixel | same | same | same | Available and referenced in `data/reference/site_elevations.json`; not re-sampled here |
| Moon Trek LRO LOLA global layer (`LRO_LOLA_DEM_Global_128ppd_v04`) | 128 pixels/degree (~237 m at the equator), 8-bit display tiles, zoom ≤ 5 | global | equirectangular tiles, no height values | NASA/JPL [Moon Trek](https://trek.nasa.gov/moon/) | **Coverage check only** at each site (tile present at zoom 5); never used for numbers |
| LROC QuickMap | imagery (WAC/NAC) and topographic basemaps | south pole | visual | NASA/ASU [quickmap.lroc.asu.edu](https://quickmap.lroc.asu.edu/) | Visual-inspection entry point; no numeric value in this document comes from it |
| LOLA 80 m/pix wide polar DEM, `LDEM_80S_80MPP_ADJ` | 80 m/pixel, 7600 × 7600 | 80°S to the pole (~608 km across, ±304 km) | same stereographic frame; surface height in metres above the 1737.4 km sphere | NASA PGDA [products/90](https://pgda.gsfc.nasa.gov/products/90), data at [LOLA_20mpp](https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/); Barker et al. 2023, *PSJ* 4, 183 | **Far tier** — ray-march from each site DEM's edge out to 150 km, 2 m eye |

## Coordinate reference system and height datum

- **Frame:** Moon Mean Earth / Polar Axis (ME), IAU selenographic planetocentric
  coordinates, longitude east-positive in [−180°, 180°). The DEMs' own WKT says
  `PROJCS[...SPHEROID["unnamed",1737400,0]...PROJECTION["Polar_Stereographic"],
  PARAMETER["latitude_of_origin",-90], PARAMETER["central_meridian",0],
  UNIT["metre",1]]` — no EPSG code exists for this lunar frame; it is defined by
  the sphere and the two parameters above.
- **Projection:** south polar stereographic, x = ρ·sin λ, y = ρ·cos λ,
  ρ = 2·1737.4 km·tan((90° + φ)/2). LunaNav uses the identical formula in
  `app/core/coords.py::polar_stereographic_xy`, so a site's DEM pixel and the
  map's pixel are the same point. Stereographic scale distortion poleward of
  85°S is below 0.2 % — far under the DEM's own accuracy.
- **Height datum:** metres above the **1737.4 km reference sphere** (LOLA Z).
  The Moon has no geoid, so "elevation" is always relative to this sphere, not
  to a sea level.
- **Grid:** north-up raster; row 0 at the top, x = left + col·5 m,
  y = top − row·5 m. NaN marks no-data cells.
- **Azimuth:** degrees clockwise from local lunar north, 0 ≤ az < 360. At a
  south-polar site, "north" points radially away from the pole — the same
  convention the visibility pipeline uses.

## How it was obtained and verified

```bash
cd backend
python scripts/inspect_site_terrain.py --download     # 5 m site DEMs (~41 MB each), write the reference
python scripts/inspect_site_terrain.py --verify-only  # re-derive from the cached DEMs and compare
python scripts/inspect_wide_terrain.py --download     # 80 m wide DEM (~181 MB), write its reference
python scripts/inspect_wide_terrain.py --verify-only  # same, offline
```

The script downloads only what is missing into `data/cache/lola_5mpp/` (git
ignored), then reads each GeoTIFF with `rasterio` and records:

1. driver, size, dtype, pixel size, extent, bounds, no-data marker;
2. the full CRS WKT, so the frame is documented from the file rather than
   assumed;
3. file size and **SHA-256**, so a later run can prove the same product;
4. coverage — whether the site falls inside the raster and the distance to each
   edge, whose minimum is the usable ray-march radius;
5. the elevation at the site pixel, plus the min/max/median height over the
   disc actually sampled, and the count of NaN cells (gaps are counted, never
   filled with zero);
6. the skyline per 1° azimuth via
   `services/horizon.build_horizon_mask_from_dem` — the same ray-march Phase 3
   uses, with lunar curvature and the observer at ground level;
7. whether Moon Trek's LOLA layer actually has a tile at the site (zoom 5).

Checks that passed on 2026-11-14 (`--verify-only` re-derives 2–6 from the cached
DEMs with no network access at all and matches the committed file):

- the site pixel elevations equal the independently committed
  `data/reference/site_elevations.json` `center_px` values to 0.01 m — the DEM
  files are the same products Phase 1 sampled;
- all three sites fall inside their DEMs, 6.3–7.7 km from the nearest edge;
- the wide DEM is 7600 × 7600 px at 80 m covering ±304 km, its checksum is
  recorded, and its heights at the three sites agree with the 5 m pixels to
  3.2 m — the expected difference between an 80 m cell and a 5 m pixel;
- the raster WKT matches the projection in `core/coords.py` (sphere 1737.4 km,
  latitude of origin −90, central meridian 0);
- Moon Trek returns a tile at zoom 5 for all three sites, and LROC QuickMap,
  Moon Trek and the PGDA page answered HTTP 200;
- no NaN cells fall inside the sampled discs.

While checking the Trek layer this exercise found a real bug: the config allowed
zoom 6 for the two LOLA layers, but Trek serves no zoom-6 tiles for them, so any
south-pole render at 2048 px would have failed. `imagery.layers.*.max_zoom` is
now 5 for both LOLA layers (LROC WAC still reaches 8).

## Limitations and missing coverage

1. **The 16 km site DEM is the near field only.** Its angles are exact at 5 m
   resolution out to 6.3–7.7 km; the masks switch to the 80 m wide DEM there, so
   a ridge narrower than ~80 m between 8 and 150 km can be missed (the far tier
   is a lower bound, not an exact skyline).
2. **Beyond 150 km is below the horizon anyway.** Terrain at 150 km on the
   1737.4 km sphere sits ~6.5 km below the tangent plane, and the last obstruction
   capable of clearing it (a 10.8 km peak) would lie at ~194 km. The masks
   therefore cover every distance from which terrain can block a body at these
   sites; only local (sub-80 m) roughness remains unresolved.
3. **Observer height changes the answer.** These summary angles use a 0 m
   observer; the masks use the 2 m eye of the Sun/Earth track. At
   `connecting-ridge`, azimuth 160°, the ground-level maximum (10.63°) comes from
   terrain 5 m away and falls to 2.83° at 2 m. Never mix the two sets of angles.
4. **Display imagery is not data.** Moon Trek's 8-bit LOLA tiles are used only to
   confirm coverage; no height or angle in this document comes from them.
5. **Slope and roughness.** Slope (medians 3.8°–8.8° over 125 m) is already in
   `data/reference/site_elevations.json`; boulders, scarps and regolith
   thickness are not represented anywhere, so this is not a hazard map.
6. **Nothing here is a landing certification**, and a clear skyline is not a
   power or communications guarantee.

## Use in Phase 3

```text
LOLA 5 m/pix DEM  (0 → 6–8 km) ─┐
                                ├─ max per azimuth, 2 m eye ─► horizon_masks/<site>.json ─► apply_mask → clearance
LOLA 80 m/pix DEM (6–8 → 150 km)┘
```

- The committed reference gives Phase 3 the DEM path, the site's pixel, the
  radius that cannot run off the raster, and a per-azimuth skyline to validate
  the mask against. `scripts/build_site_horizon_masks.py` rebuilds the masks and
  `--verify-only` checks them against this reference without the network.
- For horizons beyond the site DEMs, ingest `LDEM_875S_20M` (or a site-centred
  cut-out) in the same frame and add it as another source here before quoting
  angles from it.
- Keep the 1° azimuth step and curvature; both are already what the visibility
  pipeline expects.

## Sources

- LOLA 5 m/pix south-pole site DEMs: NASA PGDA products/78,
  <https://pgda.gsfc.nasa.gov/products/78> (Barker et al. 2021, *Planet. Space
  Sci.* 203, 105119), <https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/>
- Site numbering and coordinates: Mazarico et al. 2011, *Icarus* 211, 1066–1081,
  <https://doi.org/10.1016/j.icarus.2010.10.030>
- Moon Trek: <https://trek.nasa.gov/moon/>
- LROC QuickMap: <https://quickmap.lroc.asu.edu/>
- LOLA 80 m/pix wide polar DEM: NASA PGDA products/90,
  <https://pgda.gsfc.nasa.gov/products/90>, data at
  <https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/> (Barker et al. 2023, *Planet.
  Sci. J.* 4, 183), <https://doi.org/10.3847/PSJ/acf3e1>
