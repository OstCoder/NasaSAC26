"""Rebuild data/reference/moon_craters.json from the IAU Gazetteer of Planetary Nomenclature.

Keeps only named craters (not lettered satellite features). Needs internet, stdlib only.

Usage (from backend/):
    python scripts/fetch_craters.py
"""

from __future__ import annotations

import io
import json
import struct
import sys
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.http import get_bytes  # noqa: E402
from app.core.settings import get_settings  # noqa: E402

SOURCE_URL = "https://planetarynames.wr.usgs.gov/shapefiles/MOON_nomenclature_center_pts.zip"
CRATER_TYPE = "Crater, craters"


def read_dbf(data: bytes) -> list[dict[str, str]]:
    """Records of a dBase III table, as text. Shapefile attributes need nothing more."""
    count, header_len, record_len = struct.unpack("<xxxxIHH", data[:12])
    fields, o = [], 32
    while data[o] != 0x0D:
        fields.append((data[o:o + 11].split(b"\0")[0].decode(), data[o + 16]))
        o += 32
    records = []
    for i in range(count):
        p = header_len + i * record_len
        if data[p] == 0x2A:  # deleted record
            continue
        p += 1
        rec = {}
        for name, length in fields:
            rec[name] = data[p:p + length].decode("utf-8", "replace").strip()
            p += length
        records.append(rec)
    return records


def craters_from(records: list[dict[str, str]]) -> list[dict]:
    craters = [
        {
            "name": r["name"],
            "latitude_deg": round(float(r["center_lat"]), 4),
            # The gazetteer uses 0..360 east; LunaNav uses -180..180 east-positive.
            "longitude_deg": round((float(r["center_lon"]) + 180) % 360 - 180, 4),
            "diameter_km": round(float(r["diameter"]), 2),
        }
        for r in records
        if r["type"] == CRATER_TYPE
    ]
    return sorted(craters, key=lambda c: c["name"])


def main():
    res = get_bytes(SOURCE_URL, 120)
    if res.status != 200:
        sys.exit(f"USGS answered HTTP {res.status} for {SOURCE_URL}")
    archive = zipfile.ZipFile(io.BytesIO(res.body))
    dbf = next(n for n in archive.namelist() if n.lower().endswith(".dbf"))
    craters = craters_from(read_dbf(archive.read(dbf)))
    out = Path(get_settings().datasets["craters"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "dataset": "IAU Gazetteer of Planetary Nomenclature: lunar craters",
        "source": SOURCE_URL,
        "retrieved": date.today().isoformat(),
        "craters": craters,
    }, ensure_ascii=False, indent=0) + "\n")
    print(f"{len(craters)} craters written to {out}")


if __name__ == "__main__":
    main()
