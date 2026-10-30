# Scientific datasets

Empty by design. Scientific Mode reports "unavailable" until these exist:

- `ephemeris/sun.json`, `ephemeris/earth.json`: from `backend/scripts/fetch_horizons.py`
- `horizon_masks/<site-id>.json`: from `backend/scripts/build_horizon_mask.py` (LOLA DEM) or provided masks
- `spice/`: optional NAIF kernels for the SPICE provider

Formats and steps: `docs/ADAPTATION_GUIDE.md`, sections 3 and 4.
