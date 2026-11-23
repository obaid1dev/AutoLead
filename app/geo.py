"""Nominatim geocoding with a polite rate limit and in-memory cache."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "AutoLead/0.1 (github.com/obaid1dev/AutoLead)"
MIN_INTERVAL_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 20.0

LOCATION_NOT_FOUND = "Location not found. Try a more specific place name."
GEOCODE_UNAVAILABLE = "Could not reach OpenStreetMap's geocoder. Try again in a moment."


class LocationNotFound(Exception):
    """Raised when Nominatim has no match for the place name."""


class GeocodeError(Exception):
    """Raised when Nominatim cannot be reached or returns bad data."""


@dataclass(frozen=True)
class GeoResult:
    """A resolved place and its search bounds in Overpass order."""

    display_name: str
    bbox: tuple[float, float, float, float]  # south, west, north, east


_cache: dict[str, GeoResult] = {}
_rate_lock = asyncio.Lock()
_last_request = 0.0


def reorder_bbox(boundingbox: list[str] | list[float]) -> tuple[float, float, float, float]:
    """Convert Nominatim's bbox order to Overpass order.

    Nominatim returns ``[south, north, west, east]``; Overpass expects
    ``(south, west, north, east)``.
    """
    if len(boundingbox) != 4:
        raise GeocodeError("The geocoder returned an incomplete bounding box.")
    try:
        south, north, west, east = (float(value) for value in boundingbox)
    except (TypeError, ValueError) as exc:
        raise GeocodeError("The geocoder returned an invalid bounding box.") from exc
    if south > north or west > east:
        raise GeocodeError("The geocoder returned an invalid bounding box.")
    return (south, west, north, east)


def parse_nominatim_result(payload: list[dict]) -> GeoResult:
    """Turn a Nominatim search response into a :class:`GeoResult`."""
    if not payload:
        raise LocationNotFound(LOCATION_NOT_FOUND)
    first = payload[0]
    display_name = str(first.get("display_name") or "").strip()
    if not display_name:
        raise GeocodeError("The geocoder returned an incomplete place.")
    bbox = first.get("boundingbox")
    if not isinstance(bbox, list):
        raise GeocodeError("The geocoder returned an incomplete place.")
    return GeoResult(display_name=display_name, bbox=reorder_bbox(bbox))


async def geocode(location: str) -> GeoResult:
    """Resolve a place name to a display name and bounding box.

    Results are cached for the lifetime of the process. Outbound calls are
    spaced at least one second apart, as Nominatim's usage policy requires.
    """
    key = " ".join(location.lower().split())
    if key in _cache:
        return _cache[key]

    global _last_request
    async with _rate_lock:
        elapsed = time.monotonic() - _last_request
        if elapsed < MIN_INTERVAL_SECONDS:
            await asyncio.sleep(MIN_INTERVAL_SECONDS - elapsed)
        _last_request = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT_SECONDS,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            ) as client:
                response = await client.get(
                    NOMINATIM_URL,
                    params={"q": location, "format": "json", "limit": 1},
                )
                response.raise_for_status()
                payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise GeocodeError(GEOCODE_UNAVAILABLE) from exc
        finally:
            _last_request = time.monotonic()

    if not isinstance(payload, list):
        raise GeocodeError(GEOCODE_UNAVAILABLE)

    result = parse_nominatim_result(payload)
    _cache[key] = result
    return result
