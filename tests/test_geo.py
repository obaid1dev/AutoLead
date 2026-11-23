"""Tests for Nominatim result parsing and bounding-box reordering."""

import pytest

from app.geo import LocationNotFound, parse_nominatim_result, reorder_bbox

NOMINATIM_SAMPLE = [
    {
        "place_id": 123456,
        "display_name": "Lahore, Punjab, Pakistan",
        "boundingbox": ["31.3976", "31.6359", "74.2467", "74.4586"],
        "lat": "31.5656",
        "lon": "74.3144",
    }
]


def test_reorder_bbox_swaps_nominatim_order():
    """Nominatim's south, north, west, east becomes south, west, north, east."""
    assert reorder_bbox(["31.3976", "31.6359", "74.2467", "74.4586"]) == (
        31.3976,
        74.2467,
        31.6359,
        74.4586,
    )


def test_parse_nominatim_result_returns_display_name_and_bbox():
    """A sample response resolves to a place with usable bounds."""
    result = parse_nominatim_result(NOMINATIM_SAMPLE)

    assert result.display_name == "Lahore, Punjab, Pakistan"
    assert result.bbox == (31.3976, 74.2467, 31.6359, 74.4586)


def test_empty_nominatim_response_raises_not_found():
    """No results produce the friendly not-found error."""
    with pytest.raises(LocationNotFound, match="Location not found"):
        parse_nominatim_result([])
