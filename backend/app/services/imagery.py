"""Lunar imagery from NASA/JPL Moon Trek.

Moon Trek serves global equirectangular WMTS tiles (256 px, level 0 = 2x1
tiles, row 0 at the north edge, longitude -180..180). LunaNav:

1. fetches tiles through a disk cache (``data/cache/trek/...``), so a demo
   keeps working offline after one online run (see scripts/warm_imagery.py);
2. reprojects them into LunaNav's south polar stereographic map grid, so the
   imagery lines up exactly with sites, craters and the graticule;
3. stitches a low-zoom global texture for the 3D globe;
4. derives the globe's height and normal maps from the LOLA elevation layer;
5. serves single tiles for the whole-Moon 2D map.

Only layers listed in ``config/lunanav.config.json -> imagery.layers`` can be
requested, and only from the configured Trek host.
"""

from __future__ import annotations

import io
import math
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image

from app.core.errors import InvalidInputError, JplUnavailableError
from app.core.http import HttpError, HttpResult, get_bytes
from app.core.settings import Settings

TILE = 256
MOON_RADIUS_KM = 1737.4
# Relief is for display only. Assumes the 8-bit DEM tiles span LOLA's ~19.9 km
# global range; keep the exaggeration in step with RELIEF_SCALE in LunarGlobe.tsx.
LOLA_RANGE_M = 19_900
RELIEF_EXAGGERATION = 3
Fetcher = Callable[[str, float], HttpResult]


@dataclass(frozen=True)
class Layer:
    id: str
    label: str
    path: str
    extensions: tuple[str, ...]
    max_zoom: int
    credit: str


def rho_for_lat(lat_deg):
    return 2 * MOON_RADIUS_KM * np.tan(np.radians(90 + np.asarray(lat_deg)) / 2)


class TrekImagery:
    def __init__(self, settings: Settings, fetch: Fetcher = get_bytes):
        self.settings = settings
        self.jpl = settings.jpl
        self.cache = Path(settings.datasets["cache_dir"]) / "trek"
        self._fetch = fetch
        self._lock = threading.Lock()
        self._inflight: dict[str, threading.Lock] = {}
        self.layers = {
            k: Layer(k, v["label"], v["path"], tuple(v["extensions"]), int(v["max_zoom"]), v["credit"])
            for k, v in settings.imagery["layers"].items()
        }

    # -------------------------------------------------------------- tiles --
    def layer(self, layer_id: str) -> Layer:
        try:
            return self.layers[layer_id]
        except KeyError as exc:
            raise InvalidInputError(f"Unknown imagery layer {layer_id!r}; choose one of {sorted(self.layers)}") from exc

    def _layer_dir(self, layer: Layer) -> Path:
        # Keyed by the Trek path (not the config id) so correcting a path in the config
        # never reuses stale "no tile" markers from the old one.
        return self.cache / "tiles" / layer.path.replace("/", "__")

    def _require_coverage(self, layer: Layer, valid: np.ndarray, what: str) -> None:
        """Refuse to return imagery that is mostly empty instead of serving a black/blank picture."""
        frac = float(valid.mean()) if valid.size else 0.0
        if frac < 0.5:
            others = [k for k in self.layers if k != layer.id]
            raise JplUnavailableError(
                f"Moon Trek returned no data for {frac:.0%} coverage of the '{layer.label}' layer ({what}). "
                f"The layer path '{layer.path}' may be wrong or retired"
                + (f"; try the '{self.layers[others[0]].label}' layer instead." if others else "."),
                details={"service": "trek", "layer": layer.id, "coverage": round(frac, 3)},
            )

    def tile_url(self, layer: Layer, z: int, row: int, col: int, ext: str) -> str:
        return f"{self.jpl.trek_tiles_url}/{layer.path}/1.0.0/default/default028mm/{z}/{row}/{col}.{ext}"

    def get_tile(self, layer: Layer, z: int, row: int, col: int) -> np.ndarray | None:
        """RGB uint8 array (256x256x3), or None where Trek has no data. Raises JplUnavailableError."""
        base = self._layer_dir(layer) / str(z) / str(row)
        missing_marker = base / f"{col}.none"
        for ext in layer.extensions:
            p = base / f"{col}.{ext}"
            if p.exists():
                return np.asarray(Image.open(p).convert("RGB"))
        if missing_marker.exists():
            return None

        key = f"{layer.id}/{z}/{row}/{col}"
        with self._lock:
            lock = self._inflight.setdefault(key, threading.Lock())
        with lock:
            for ext in layer.extensions:
                p = base / f"{col}.{ext}"
                if p.exists():
                    return np.asarray(Image.open(p).convert("RGB"))
            for ext in layer.extensions:
                url = self.tile_url(layer, z, row, col, ext)
                try:
                    try:
                        res = self._fetch(url, self.jpl.trek_timeout_s)
                    except HttpError:
                        res = self._fetch(url, self.jpl.trek_timeout_s)  # one retry for transient timeouts
                except HttpError as e:
                    raise JplUnavailableError(
                        f"Could not reach NASA/JPL Moon Trek ({e}). Check your internet connection; "
                        "previously viewed imagery stays available from the local cache.",
                        details={"service": "trek", "url": self.jpl.trek_tiles_url},
                    ) from e
                if res.status == 200 and res.body:
                    try:
                        img = Image.open(io.BytesIO(res.body)).convert("RGB")
                    except Exception:  # not an image (error page)
                        continue
                    base.mkdir(parents=True, exist_ok=True)
                    (base / f"{col}.{ext}").write_bytes(res.body)
                    return np.asarray(img)
                if res.status not in (404, 400):
                    raise JplUnavailableError(
                        f"Moon Trek answered HTTP {res.status} for layer {layer.id}.",
                        details={"service": "trek", "status": res.status},
                    )
            base.mkdir(parents=True, exist_ok=True)
            missing_marker.write_text("no tile")
            return None

    def tile_bytes(self, layer_id: str, z: int, row: int, col: int) -> tuple[bytes, str] | None:
        """Encoded tile and its media type, or None where Trek has no data."""
        layer = self.layer(layer_id)
        if not (0 <= z <= layer.max_zoom and 0 <= row < 2 ** z and 0 <= col < 2 ** (z + 1)):
            raise InvalidInputError(f"No tile {z}/{row}/{col} in layer {layer_id!r}")
        if self.get_tile(layer, z, row, col) is None:
            return None
        base = self._layer_dir(layer) / str(z) / str(row)
        for ext in layer.extensions:
            p = base / f"{col}.{ext}"
            if p.exists():
                return p.read_bytes(), "image/jpeg" if ext == "jpg" else f"image/{ext}"
        return None

    def _mosaic(self, layer: Layer, z: int, rows: range) -> tuple[np.ndarray, np.ndarray]:
        """Stitch full-longitude bands for ``rows``. Returns (rgb float32, valid mask)."""
        cols = 2 ** (z + 1)
        out = np.zeros((len(rows) * TILE, cols * TILE, 3), np.float32)
        valid = np.zeros(out.shape[:2], bool)
        jobs = [(r, c) for r in rows for c in range(cols)]
        with ThreadPoolExecutor(max_workers=self.jpl.trek_max_parallel_requests) as pool:
            for (r, c), tile in zip(jobs, pool.map(lambda rc: self.get_tile(layer, z, *rc), jobs)):
                if tile is None:
                    continue
                y0 = (r - rows.start) * TILE
                out[y0:y0 + TILE, c * TILE:(c + 1) * TILE] = tile[:TILE, :TILE]
                valid[y0:y0 + TILE, c * TILE:(c + 1) * TILE] = True
        return out, valid

    # ------------------------------------------------------- south pole --
    def choose_zoom(self, layer: Layer, size_px: int, max_lat: float) -> int:
        """Smallest zoom whose latitude resolution is >= ~85% of the output's."""
        out_px_per_deg = size_px / (2 * (90 + max_lat))
        for z in range(0, layer.max_zoom + 1):
            if TILE * 2 ** z / 180 >= 0.85 * out_px_per_deg:
                return z
        return layer.max_zoom

    def south_pole_png(self, layer_id: str, size_px: int = 2048, max_lat: float = -80.0) -> tuple[bytes, dict]:
        if not -89.0 <= max_lat <= -60.0:
            raise InvalidInputError("max_lat must be between -89 and -60")
        if not 256 <= size_px <= 4096:
            raise InvalidInputError("size_px must be between 256 and 4096")
        layer = self.layer(layer_id)
        z = self.choose_zoom(layer, size_px, max_lat)
        out = self._layer_dir(layer) / "rendered" / f"south_pole_{size_px}_{abs(max_lat):g}_z{z}.png"
        meta = {"layer": layer.id, "zoom": z, "max_lat": max_lat, "size_px": size_px,
                "half_width_km": float(rho_for_lat(max_lat)), "credit": layer.credit}
        if out.exists():
            return out.read_bytes(), meta

        deg_per_row = 180 / 2 ** z
        first_row = int(math.floor((90 - max_lat) / deg_per_row))  # row containing max_lat
        rows = range(min(first_row, 2 ** z - 1), 2 ** z)
        mosaic, valid = self._mosaic(layer, z, rows)
        self._require_coverage(layer, valid, "south polar region")
        lat_top = 90 - rows.start * deg_per_row
        px_per_deg = TILE / deg_per_row

        R = float(rho_for_lat(max_lat))
        c = (np.arange(size_px) + 0.5) / size_px * 2 * R - R
        x, y = np.meshgrid(c, -c)  # row 0 = +y (0° meridian, top)
        rho = np.hypot(x, y)
        lat = -90 + 2 * np.degrees(np.arctan(rho / (2 * MOON_RADIUS_KM)))
        lon = np.degrees(np.arctan2(x, y))
        fy = (lat_top - lat) * px_per_deg - 0.5
        fx = ((lon + 180) % 360) * px_per_deg - 0.5
        rgb, ok = _bilinear(mosaic, valid, fx, fy)
        alpha = ((lat <= max_lat) & ok).astype(np.uint8) * 255
        img = Image.fromarray(np.dstack([rgb, alpha]), "RGBA")
        buf = io.BytesIO()
        img.save(buf, "PNG", optimize=True)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(buf.getvalue())
        return buf.getvalue(), meta

    # ----------------------------------------------------------- global --
    def global_jpeg(self, layer_id: str, zoom: int = 2) -> tuple[bytes, dict]:
        layer = self.layer(layer_id)
        if not 0 <= zoom <= min(3, layer.max_zoom):
            raise InvalidInputError("zoom must be between 0 and 3 for the global texture")
        out = self._layer_dir(layer) / "rendered" / f"global_z{zoom}.jpg"
        meta = {"layer": layer.id, "zoom": zoom, "credit": layer.credit}
        if out.exists():
            return out.read_bytes(), meta
        mosaic, valid = self._mosaic(layer, zoom, range(0, 2 ** zoom))
        self._require_coverage(layer, valid, "global texture")
        buf = io.BytesIO()
        Image.fromarray(mosaic.clip(0, 255).astype(np.uint8)).save(buf, "JPEG", quality=88)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(buf.getvalue())
        return buf.getvalue(), meta

    def relief_jpeg(self, kind: str, zoom: int = 2) -> tuple[bytes, dict]:
        """Equirectangular height map (grey) or tangent-space normal map from the LOLA DEM tiles."""
        if kind not in ("height", "normal"):
            raise InvalidInputError("kind must be 'height' or 'normal'")
        layer = self.layer(self.settings.imagery["relief_layer"])
        if not 0 <= zoom <= min(3, layer.max_zoom):
            raise InvalidInputError("zoom must be between 0 and 3 for the relief maps")
        out = self._layer_dir(layer) / "rendered" / f"relief_{kind}_z{zoom}.jpg"
        meta = {"layer": layer.id, "zoom": zoom, "kind": kind, "credit": layer.credit}
        if out.exists():
            return out.read_bytes(), meta
        mosaic, valid = self._mosaic(layer, zoom, range(0, 2 ** zoom))
        self._require_coverage(layer, valid, "relief map")
        height = _smooth(mosaic[..., 0])
        rgb = np.dstack([height] * 3) if kind == "height" else _normal_map(height)
        buf = io.BytesIO()
        Image.fromarray(rgb.clip(0, 255).astype(np.uint8)).save(buf, "JPEG", quality=92)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(buf.getvalue())
        return buf.getvalue(), meta

    # ----------------------------------------------------------- status --
    def probe(self) -> HttpResult:
        layer = self.layer(self.settings.imagery["default_layer"])
        last = None
        for ext in layer.extensions:
            last = self._fetch(self.tile_url(layer, 0, 0, 0, ext), min(self.jpl.trek_timeout_s, 10))
            if last.status == 200:
                return last
        return last


def _bilinear(img: np.ndarray, valid: np.ndarray, fx: np.ndarray, fy: np.ndarray):
    h, w = img.shape[:2]
    x0 = np.floor(fx).astype(int)
    y0 = np.floor(fy).astype(int)
    tx, ty = fx - x0, fy - y0
    x1 = (x0 + 1) % w  # longitude wraps
    x0 %= w
    y0c = np.clip(y0, 0, h - 1)
    y1c = np.clip(y0 + 1, 0, h - 1)
    ok = valid[y0c, x0] & valid[y0c, x1] & valid[y1c, x0] & valid[y1c, x1]
    out = (img[y0c, x0] * ((1 - tx) * (1 - ty))[..., None] + img[y0c, x1] * (tx * (1 - ty))[..., None]
           + img[y1c, x0] * ((1 - tx) * ty)[..., None] + img[y1c, x1] * (tx * ty)[..., None])
    return out.clip(0, 255).astype(np.uint8), ok


def _smooth(h: np.ndarray, passes: int = 4) -> np.ndarray:
    """Binomial blur that hides 8-bit height steps. Longitude wraps; latitude clamps at the poles."""
    for _ in range(passes):
        h = (np.roll(h, 1, 1) + 2 * h + np.roll(h, -1, 1)) / 4
        h = (np.vstack([h[:1], h[:-1]]) + 2 * h + np.vstack([h[1:], h[-1:]])) / 4
    return h


def _normal_map(height: np.ndarray) -> np.ndarray:
    """RGB normals for an equirectangular height map: +x east, +y north (row 0 is the north edge)."""
    rows, cols = height.shape
    px_m = 2 * math.pi * MOON_RADIUS_KM * 1000 / cols
    lat = np.radians(90 - (np.arange(rows) + 0.5) * 180 / rows)
    # Near the poles, pixels get very narrow in longitude; the floor stops slopes blowing up.
    cos_lat = np.maximum(np.cos(lat), 0.05)[:, None]
    slope = RELIEF_EXAGGERATION * (LOLA_RANGE_M / 255) / px_m
    d_east = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) / 2 * slope / cos_lat
    d_north = (np.vstack([height[:1], height[:-1]]) - np.vstack([height[1:], height[-1:]])) / 2 * slope
    length = np.sqrt(d_east ** 2 + d_north ** 2 + 1)
    return (np.dstack([-d_east, -d_north, np.ones_like(height)]) / length[..., None] + 1) * 127.5


_instance: TrekImagery | None = None


def get_imagery() -> TrekImagery:
    global _instance
    if _instance is None:
        from app.core.settings import get_settings
        _instance = TrekImagery(get_settings())
    return _instance
