"""Domain errors. The API layer maps these to structured HTTP responses.

LunaNav never substitutes fabricated values when real data is missing: a
provider that cannot answer raises :class:`DataUnavailableError`.
"""

from __future__ import annotations


class LunaNavError(Exception):
    code = "LUNANAV_ERROR"
    http_status = 400

    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidInputError(LunaNavError):
    code = "INVALID_INPUT"
    http_status = 422


class OutOfSupportedRangeError(LunaNavError):
    code = "OUT_OF_SUPPORTED_RANGE"
    http_status = 422


class DataUnavailableError(LunaNavError):
    """Required scientific data (ephemeris table, terrain mask, kernel) is missing."""

    code = "SCIENTIFIC_DATA_UNAVAILABLE"
    http_status = 503


class UnknownSiteError(LunaNavError):
    code = "UNKNOWN_SITE"
    http_status = 404
