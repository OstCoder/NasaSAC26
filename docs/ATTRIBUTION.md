# Attribution, data sources and licenses

LunaNav combines NASA-derived data with its own calculations. The application is not a NASA product and is not approved, certified or endorsed by NASA.

## Code license

The source code in this repository is released under the [MIT License](../LICENSE). That license applies to the code written for LunaNav, not to third-party data, imagery or dependencies.

## NASA and partner data

| Data | Product / version used | Provider | Access / evidence | How LunaNav uses it |
| --- | --- | --- | --- | --- |
| Sun and Earth observer geometry | JPL Horizons API, observer `coord@301` at each candidate; monthly query cache | NASA/Jet Propulsion Laboratory | Live checks recorded 2026-11-14; committed series generated from Horizons | Primary Sun/Earth azimuth, elevation and range for the two mission windows |
| Lunar terrain | LOLA 5 m/pixel site DEMs (16 km × 16 km) and the 80 m/pixel wide polar DEM | NASA/GSFC LRO LOLA team; NASA PGDA | Retrieved 2026-11-14; checksums and extents recorded in `data/reference/site_terrain.json` and `data/reference/wide_dem.json` | Terrain skyline, clearance and terrain-adjusted visibility; 125 m previews for the optional 3D view |
| PSR boundaries | `LOLA_PSR_75S_120M_82S_060M_5KM2_FINAL`, companion to `NAC_POLE_PSR_SOUTH`; 5 km² threshold | NASA/GSFC/Arizona State University LROC team | Committed catalogue built 2026-11-14; 653 polygons | Mapped PSR outlines, boundary/centroid proximity and science context |
| Lunar imagery | LROC WAC mosaic and LOLA shaded relief / elevation tiles | NASA/GSFC/Arizona State University LROC; NASA/GSFC LOLA; NASA/JPL Moon Trek | Layer paths checked against Moon Trek on 2026-10-30; zooms rechecked 2026-11-14 | Polar map, whole-Moon map and 3D Moon display |
| Crater names and centres | IAU Gazetteer subset | International Astronomical Union / USGS | Committed `data/reference/moon_craters.json`; 1,615 entries | Map labels and context |
| Lunar radius and frame | 1,737.4 km mean sphere; Mean Earth / Polar Axis, east-positive planetocentric longitude | IAU / NASA conventions | Declared in `config/lunanav.config.json` | Coordinate transforms, distances and terrain geometry |

NASA data are generally not protected by U.S. copyright, but that does not mean NASA endorses this project. Imagery and third-party services remain subject to their own terms. Do not describe LunaNav as an official NASA product.

### Scientific references

- Mazarico, E., Neumann, G. A., Smith, D. E., Zuber, M. T., & Solomon, S. C. (2011). Illumination conditions of the lunar polar regions using LOLA topography. *Icarus*, 211(2), 1066–1081.
- NASA/JPL Horizons System: <https://ssd.jpl.nasa.gov/horizons/>
- NASA LOLA south-pole topography (PGDA product 78): <https://pgda.gsfc.nasa.gov/products/78>
- NASA LROC QuickMap: <https://quickmap.lroc.asu.edu/>
- NASA Moon Trek: <https://trek.nasa.gov/moon/>
- NASA Space Apps Challenge 2026: <https://www.spaceappschallenge.org/2026/>
- Canadian Space Agency lunar exploration background: <https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/>

## Software dependencies

LunaNav is built with open-source software. The main runtime and development dependencies are:

| Area | Packages |
| --- | --- |
| Backend | FastAPI, Uvicorn, Pydantic, NumPy, Pillow |
| Frontend | React, React DOM, TypeScript, Vite, Tailwind CSS, Radix UI, Lucide, Leaflet, React Leaflet, Recharts, Three.js |
| Tests / automation | pytest, HTTPX, Vitest, Testing Library, Playwright Core |

Their licenses remain with their respective projects. Before redistributing a bundled build, check the license metadata in `frontend/package-lock.json`, the installed Python packages, and the upstream repositories. The project does not relicense those dependencies.

## LunaNav calculations

The following are original LunaNav calculations, not NASA products:

- topocentric visibility intervals and metrics;
- terrain-horizon masks and the 2D skyline profile;
- requirement evaluation and mission-delay comparison;
- solar-power, battery and link-budget demonstrations;
- decision-support scoring and explanations;
- PSR boundary/centroid distance calculations;
- the local 3D shadow ray-march.

Every result carries its source and uncertainty context in the application and the linked methodology documents.
