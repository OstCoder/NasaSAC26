"""Parsing the USGS nomenclature table into the crater catalogue."""

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from fetch_craters import craters_from, read_dbf  # noqa: E402


def _dbf(fields: list[tuple[str, int]], rows: list[tuple[bytes, list[str]]]) -> bytes:
    record_len = 1 + sum(n for _, n in fields)
    header_len = 32 + 32 * len(fields) + 1
    out = bytearray(struct.pack("<BBBBIHH", 3, 0, 0, 0, len(rows), header_len, record_len) + bytes(20))
    for name, n in fields:
        out += name.encode().ljust(11, b"\0") + b"C" + bytes(4) + bytes([n]) + bytes(15)
    out += b"\x0d"
    for flag, values in rows:
        out += flag
        for (_, n), v in zip(fields, values):
            out += v.encode().ljust(n)
    return bytes(out)


FIELDS = [("name", 20), ("center_lat", 10), ("center_lon", 10), ("diameter", 10), ("type", 20)]


def test_keeps_live_craters_and_converts_longitude():
    rows = [
        (b" ", ["Poincar\u00e9", "-57.3", "348.78", "85.3", "Crater, craters"]),
        (b" ", ["Tycho A", "-40", "10", "29", "Satellite Feature"]),
        (b"*", ["Deleted", "0", "0", "1", "Crater, craters"]),
    ]
    craters = craters_from(read_dbf(_dbf(FIELDS, rows)))
    assert [c["name"] for c in craters] == ["Poincar\u00e9"]
    assert craters[0]["longitude_deg"] == -11.22 and craters[0]["latitude_deg"] == -57.3
