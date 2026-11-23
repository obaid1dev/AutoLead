"""Build and run Overpass queries, then turn OSM elements into businesses."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from .categories import CATEGORIES_BY_KEY, label_for_tags
from .models import Business

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "AutoLead/0.1 (github.com/obaid1dev/AutoLead)"
REQUEST_TIMEOUT_SECONDS = 90.0
RETRY_DELAYS = (6.0, 18.0)
CACHE_TTL_SECONDS = 600

OVERPASS_BUSY = "Overpass is busy right now, try again in a minute."

# Ordered so `contact:*` wins over a bare tag and one link per platform is kept.
SOCIAL_KEYS: tuple[tuple[str, str], ...] = (
    ("contact:facebook", "Facebook"),
    ("facebook", "Facebook"),
    ("contact:instagram", "Instagram"),
    ("instagram", "Instagram"),
    ("contact:twitter", "Twitter / X"),
    ("twitter", "Twitter / X"),
    ("contact:x", "Twitter / X"),
    ("contact:youtube", "YouTube"),
    ("youtube", "YouTube"),
    ("contact:linkedin", "LinkedIn"),
    ("linkedin", "LinkedIn"),
    ("contact:tiktok", "TikTok"),
    ("tiktok", "TikTok"),
    ("contact:whatsapp", "WhatsApp"),
    ("whatsapp", "WhatsApp"),
    ("contact:telegram", "Telegram"),
    ("telegram", "Telegram"),
    ("contact:mastodon", "Mastodon"),
    ("mastodon", "Mastodon"),
)

_cache: dict[tuple[Any, ...], tuple[float, list[Business]]] = {}


class OverpassError(Exception):
    """Raised when Overpass cannot complete a search."""


def _clean(value: Any) -> str | None:
    """Return a stripped string, or ``None`` for missing/placeholder values."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or text.lower() in {"no", "none", "n/a"}:
        return None
    return text


def _first_tag(tags: dict[str, str], *keys: str) -> str | None:
    """Return the first non-empty value among several tag keys."""
    for key in keys:
        value = _clean(tags.get(key))
        if value:
            return value
    return None


def _address(tags: dict[str, str]) -> str | None:
    """Join OSM address parts into one readable line."""
    street = " ".join(
        part
        for part in (_clean(tags.get("addr:housenumber")), _clean(tags.get("addr:street")))
        if part
    )
    parts = [
        street or None,
        _clean(tags.get("addr:city")),
        _clean(tags.get("addr:postcode")),
    ]
    joined = ", ".join(part for part in parts if part)
    return joined or _clean(tags.get("addr:full"))


def _socials(tags: dict[str, str]) -> dict[str, str]:
    """Collect known social profiles, preferring ``contact:*`` tags."""
    found: dict[str, str] = {}
    for key, label in SOCIAL_KEYS:
        if label in found:
            continue
        value = _clean(tags.get(key))
        if value:
            found[label] = value
    return found


def _coordinates(element: dict[str, Any]) -> tuple[float, float] | None:
    """Return latitude/longitude for a node, or the center of a way/relation."""
    center = element.get("center")
    center = center if isinstance(center, dict) else {}
    try:
        return float(element.get("lat", center.get("lat"))), float(
            element.get("lon", center.get("lon"))
        )
    except (TypeError, ValueError):
        return None


def build_query(bbox: tuple[float, float, float, float], category: str = "all") -> str:
    """Build an Overpass QL query within ``(south, west, north, east)`` bounds."""
    category_def = CATEGORIES_BY_KEY.get(category)
    if category_def is None:
        raise ValueError(f"Unknown category: {category}")
    south, west, north, east = bbox
    bounds = f"{south:.6f},{west:.6f},{north:.6f},{east:.6f}"

    clauses = []
    for key, pattern in category_def.filters:
        selector = f'["{key}"]' if pattern is None else f'["{key}"~"{pattern}"]'
        clauses.append(f'  nwr["name"]{selector}({bounds});')

    return "[out:json][timeout:60];\n(\n" + "\n".join(clauses) + "\n);\nout center tags;"


def parse_element(element: dict[str, Any]) -> Business | None:
    """Convert one Overpass element to a :class:`Business`, or skip it."""
    if not isinstance(element, dict):
        return None
    tags = element.get("tags")
    if not isinstance(tags, dict):
        return None
    name = _clean(tags.get("name"))
    if not name:
        return None

    element_type = element.get("type")
    element_id = element.get("id")
    if element_type not in {"node", "way", "relation"} or element_id is None:
        return None
    if _coordinates(element) is None:
        return None

    website = _first_tag(tags, "website", "contact:website", "url")
    return Business(
        name=name,
        category=label_for_tags(tags),
        description=_first_tag(tags, "description", "note"),
        phone=_first_tag(tags, "phone", "contact:phone"),
        email=_first_tag(tags, "email", "contact:email"),
        address=_address(tags),
        opening_hours=_first_tag(tags, "opening_hours"),
        socials=_socials(tags),
        website=website,
        has_website=website is not None,
        osm_url=f"https://www.openstreetmap.org/{element_type}/{element_id}",
    )


def _merge(existing: Business, incoming: Business) -> Business:
    """Fill gaps in the first duplicate with data from the second."""
    updates: dict[str, Any] = {}
    for field in ("description", "phone", "email", "address", "opening_hours", "website"):
        if getattr(existing, field) is None and getattr(incoming, field) is not None:
            updates[field] = getattr(incoming, field)
    if "website" in updates:
        updates["has_website"] = True
    socials = {**incoming.socials, **existing.socials}
    if socials != existing.socials:
        updates["socials"] = socials
    return existing.model_copy(update=updates) if updates else existing


def parse_elements(elements: list[Any]) -> list[Business]:
    """Parse and deduplicate Overpass elements, skipping malformed ones."""
    merged: dict[tuple[str, float, float], Business] = {}
    order: list[tuple[str, float, float]] = []

    for element in elements:
        business = parse_element(element)
        if business is None:
            continue
        lat_lon = _coordinates(element)
        if lat_lon is None:
            continue
        key = (business.name.casefold(), round(lat_lon[0], 5), round(lat_lon[1], 5))
        if key in merged:
            merged[key] = _merge(merged[key], business)
        else:
            merged[key] = business
            order.append(key)

    return [merged[key] for key in order]


def select_results(
    businesses: list[Business],
    only_without_website: bool = True,
    limit: int = 200,
) -> list[Business]:
    """Filter, sort, and cap parsed businesses.

    Businesses with a phone or email come first, then alphabetical by name.
    """
    visible = [
        business
        for business in businesses
        if not (only_without_website and business.has_website)
    ]
    visible.sort(key=lambda business: (not (business.phone or business.email), business.name.casefold()))
    return visible[:limit]


async def _fetch(query: str) -> dict[str, Any]:
    """POST a query to Overpass, backing off while the service is busy."""
    for delay in (*RETRY_DELAYS, None):
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT_SECONDS,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            ) as client:
                response = await client.post(OVERPASS_URL, data={"data": query})
        except httpx.HTTPError as exc:
            raise OverpassError(OVERPASS_BUSY) from exc

        if response.status_code == 200:
            try:
                payload = response.json()
            except ValueError as exc:
                raise OverpassError(OVERPASS_BUSY) from exc
            if isinstance(payload, dict) and isinstance(payload.get("elements"), list):
                return payload
            raise OverpassError(OVERPASS_BUSY)

        if response.status_code in {429, 502, 503, 504} and delay is not None:
            await asyncio.sleep(delay)
            continue
        raise OverpassError(OVERPASS_BUSY)

    raise OverpassError(OVERPASS_BUSY)


async def search_businesses(
    bbox: tuple[float, float, float, float],
    category: str = "all",
    only_without_website: bool = True,
    limit: int = 200,
) -> list[Business]:
    """Search Overpass and return filtered businesses.

    Identical searches are cached in memory for ten minutes to stay polite
    to the public Overpass instance.
    """
    cache_key = (
        tuple(round(value, 6) for value in bbox),
        category,
        only_without_website,
        limit,
    )
    cached = _cache.get(cache_key)
    if cached is not None and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        return list(cached[1])

    payload = await _fetch(build_query(bbox, category))
    results = select_results(
        parse_elements(payload["elements"]),
        only_without_website=only_without_website,
        limit=limit,
    )
    _cache[cache_key] = (time.monotonic(), results)
    return list(results)
