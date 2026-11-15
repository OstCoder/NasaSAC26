# Phase 6 science — PSR context, terrain illumination and transparency

Phase 6 adds a science-focused view on top of the Phase 1–5 calculation stack. It does not replace the terrain-adjusted visibility engine, the mission requirements or the Phase 5 power model. The new layer answers a narrower question: **which mapped permanently shadowed regions are near a candidate, and what can—and cannot—be inferred from that?**

## 1. PSR dataset and provenance

The committed catalogue is `data/reference/psrs.json`, built by `backend/scripts/build_psr_catalogue.py` from the LROC south-pole PSR product:

- **Product:** `NAC_POLE_PSR_SOUTH` companion shapefile, `LOLA_PSR_75S_120M_82S_060M_5KM2_FINAL`.
- **Provider:** NASA/GSFC/Arizona State University LROC team.
- **Derived from:** LOLA permanent-shadow masks (Mazarico et al. 2011, *Icarus* 211, 1066–1081).
- **Coverage:** south polar region, 653 mapped polygons in the committed file; the map/science default is the 390 polygons poleward of 80°S.
- **Area threshold:** 5 km². Smaller shadow patches are not represented, even where the site notes quote published sub-kilometre PSRs.
- **Boundary resolution:** 120 m at 75–82°S and 60 m poleward of 82°S.
- **Projection:** south polar stereographic on a 1737.4 km sphere; `x = rho·sin(lon)`, `y = rho·cos(lon)`, east-positive longitude.

The catalogue is a set of **traced shadow boundaries**, not a water-ice map, a thermal map, a hazard map or a rover-scale surface model.

### Candidate context

The site catalogue enriches each landing site at load time, using the same `PsrCatalogue` geometry as the map and API:

| Site | Nearest mapped PSR | Boundary distance | Mapped area | Mapped PSRs within 10 km |
|---|---|---:|---:|---:|
| `shackleton-rim` | PSR near Shackleton (`SP_896450_1282030`) | 2.479 km | 233.7 km² | 1 |
| `connecting-ridge` | PSR near Spudis (`SP_895060_2806850`) | 11.515 km | 53.3 km² | 0 |
| `de-gerlache-rim` | PSR near de Gerlache (`SP_883120_2691430`) | 12.106 km | 243.4 km² | 0 |

These values are reproduced by `GET /api/science/nearest-psr` and by the Science page.

## 2. Distance method

For the **nearest boundary**, the service computes the minimum point-to-segment distance from the projected site point to every ring of every polygon. It returns **zero** when the point is inside a polygon. This uses the same south-polar stereographic plane as the 2D map; scale error is below 0.2% poleward of 85°S.

For the **centroid distance**, it uses the haversine formula on the mean lunar sphere:

```text
a = sin²(Δlat/2) + cos(lat1)·cos(lat2)·sin²(Δlon/2)
c = 2·atan2(√a, √(1−a))
d = R·c, with R = 1737.4 km
```

The response reports both values, the mapped area and a positional uncertainty of ±60 m at the candidate latitudes. Neither is a traverse distance. Accessibility also depends on slope, crater walls, boulders, thermal limits, power and rover capability; none of those is inferred.

## 3. Water-ice status

The science response always reports:

```json
{
  "water_ice_confirmed": null,
  "water_ice_status": "not_assessed",
  "water_ice_evidence": []
}
```

**Unknown is not evidence of absence.** A nearby PSR is a lead for investigation. No committed data in this repository supports an ice detection, concentration, depth, temperature or resource estimate. The UI says this in the Science page, the decision-support science mode and the documentation.

## 4. Map and science UI

- The planner and Science page both expose a **PSR layer** toggle.
- The nearest mapped PSR to the selected site is outlined in gold and labelled with its area.
- The legend identifies the LROC/LOLA product and the >5 km² threshold.
- The Science page adds a site context card with boundary/centroid distances, uncertainty, terrain basis, both committed mission windows, water-ice status, sources and explicit limits.
- The same page carries six educational topics and the model-label vocabulary (geometric, terrain-aware, simplified energy, unavailable data).

## 5. 3D terrain and illumination

The 3D panel uses the existing `data/scientific/site_dems/*.json` previews: 128 × 128 average-pooled LOLA cells at 125 m, with the source file and SHA-256 in the response. Three.js is lazy-loaded only after the user enables the view.

The displayed terrain is vertically exaggerated and labelled. A blue marker is placed at the source site cell. A local ray-march samples up to 96 cells (~12 km) toward the Sun and darkens cells whose terrain rises above the Sun ray; a local facet test rejects slopes facing away from the Sun. This is **display illumination**, not a replacement for the committed 360-point horizon mask and not a PSR classifier. The 2D terrain-horizon profile remains the authority for visibility numbers.

## 6. Mission-time animation

The existing visibility timeline now exposes 0.5×, 1×, 2× and 4× playback. Playback updates the same inspected sample used by the snapshot, sky view, horizon panorama and 3D scene. The next modelled visibility edge is displayed and marked on the chart when it falls inside the current range. Playback stops at the last sample; no sample is invented outside the stored window. The committed series is hourly, with interval edges interpolated from clearance.

## 7. API

| Endpoint | Purpose |
|---|---|
| `GET /api/science/psrs` | PSR polygons plus source, projection, area threshold and limits |
| `GET /api/science/nearest-psr?site_id=…` or `?latitude_deg=…&longitude_deg=…` | Nearest boundary/centroid distance, nearby regions, uncertainty and water-ice status |
| `GET /api/science/site-context?site_id=…` | Site, PSR, terrain coverage, both visibility windows, science status and limits |
| `GET /api/terrain/mesh?site_id=…` | Alias of the committed pooled DEM used by the 3D view |

All endpoints are application endpoints, not NASA APIs.

## 8. Validation and limits

Automated coverage:

- `backend/tests/test_science.py` — catalogue metadata, candidate distances, a point inside a PSR giving 0 km, empty near-radius behavior, unknown site and ambiguous query handling, site context, water-ice nulls and mesh alias.
- `backend/tests/test_sites_psr.py` — existing polygon containment, centroid haversine and within-radius checks.
- `frontend/src/features/phase3/terrainShadow.test.ts` — flat lighting, sub-horizon darkening, east-wall shadow and opposite-Sun behavior.
- `frontend/src/features/visibility/timeline.test.ts` — next-transition selection and date assertions.
- `frontend/scripts/acceptance-phase6.mjs` — 8 browser/API checks including 390 px.

Known limits:

- PSRs below 5 km² are absent; "no mapped PSR nearby" does not mean no small shadow exists.
- The boundary product is a traced mask, not a landing-hazard or trafficability model.
- Terrain previews are pooled to 125 m; they cannot resolve boulders, a landing ellipse or a route.
- The 3D shadow ray-march is local and illustrative; it is not the visibility calculation.
- Water-ice concentration and temperature are not available in the committed datasets.
- No claim of NASA approval, flight readiness or landing safety is made.
