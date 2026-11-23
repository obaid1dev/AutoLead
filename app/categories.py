"""Business categories and the OpenStreetMap tags used to find them.

Each category maps a human-facing label to one or more OSM tag filters.
A filter is a ``(key, regex)`` pair; ``regex=None`` matches any value for
that key. Regular expressions are deliberately kept short and anchored.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    """A selectable business category and its Overpass filters."""

    key: str
    label: str
    filters: tuple[tuple[str, str | None], ...]


_RESTAURANT = r"^(restaurant|fast_food)$"
_CAFE = r"^(cafe|ice_cream)$"
_BEAUTY = r"^(beauty|hairdresser|massage|tattoo|nail_salon)$"
_HEALTH = r"^(dentist|doctors|clinic|pharmacy)$"
_CAR_REPAIR = r"^(car_repair|car_parts|tyres)$"
_HOTEL = r"^(hotel|guest_house|hostel|motel)$"
_GYM = r"^(fitness_centre|sports_centre)$"

# Business-like amenities used when the user asks for everything.
_AMENITY_ALL = (
    r"^(restaurant|fast_food|cafe|bar|pub|ice_cream|dentist|doctors|clinic|"
    r"pharmacy|veterinary|fuel|car_wash|car_rental|bureau_de_change|spa)$"
)
_LEISURE_ALL = r"^(fitness_centre|sports_centre|bowling_alley|dance|escape_game)$"
_TOURISM_ALL = r"^(hotel|guest_house|hostel|motel)$"

ALL_FILTERS: tuple[tuple[str, str | None], ...] = (
    ("shop", None),
    ("amenity", _AMENITY_ALL),
    ("office", None),
    ("craft", None),
    ("healthcare", None),
    ("leisure", _LEISURE_ALL),
    ("tourism", _TOURISM_ALL),
)

CATEGORIES: tuple[Category, ...] = (
    Category("all", "All businesses", ALL_FILTERS),
    Category("restaurant", "Restaurant", (("amenity", _RESTAURANT),)),
    Category("cafe", "Cafe", (("amenity", _CAFE),)),
    Category("clothing", "Clothing", (("shop", r"^(clothes|shoes|fashion|boutique|tailor)$"),)),
    Category("beauty", "Beauty & salon", (("shop", _BEAUTY),)),
    Category("health", "Dentist & clinic", (("amenity", _HEALTH), ("healthcare", None))),
    Category("car_repair", "Car repair", (("shop", _CAR_REPAIR), ("craft", _CAR_REPAIR))),
    Category("hotel", "Hotel", (("tourism", _HOTEL),)),
    Category("gym", "Gym", (("leisure", _GYM),)),
    Category("shops", "Shops & retail", (("shop", None),)),
)

CATEGORIES_BY_KEY: dict[str, Category] = {category.key: category for category in CATEGORIES}

# Specific categories in matching order. "all" and the broad "shops" category
# come last so a clothing shop or hair salon gets its more useful label.
_MATCH_ORDER: tuple[Category, ...] = tuple(
    category for category in CATEGORIES if category.key not in {"all", "shops"}
)

_TAG_KEYS = ("shop", "amenity", "office", "craft", "healthcare", "leisure", "tourism")


def _matches(tags: dict[str, str], key: str, pattern: str | None) -> bool:
    """Return whether a tag key/value pair satisfies a category filter."""
    value = tags.get(key)
    if not value:
        return False
    if pattern is None:
        return True
    try:
        return re.fullmatch(pattern, value) is not None
    except re.error:  # pragma: no cover - filters are authored above
        return False


def label_for_tags(tags: dict[str, str]) -> str:
    """Return a short, human-readable category label for an element's tags."""
    for category in _MATCH_ORDER:
        if any(_matches(tags, key, pattern) for key, pattern in category.filters):
            return category.label

    for key in _TAG_KEYS:
        value = tags.get(key)
        if value:
            # Retail is broad, so name the shop type instead (Bakery, Florist…).
            return value.replace("_", " ").replace("-", " ").capitalize()

    return "Business"


def category_options() -> list[dict[str, str]]:
    """Return the category list for the API dropdown."""
    return [{"key": category.key, "label": category.label} for category in CATEGORIES]
