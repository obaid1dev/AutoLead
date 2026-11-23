"""Tests for Overpass query building, element parsing, and result filtering."""

from app.overpass import build_query, parse_elements, select_results

SAMPLE_ELEMENTS = [
    {
        "type": "node",
        "id": 101,
        "lat": 31.5204,
        "lon": 74.3587,
        "tags": {
            "name": "Zam Zam Restaurant",
            "amenity": "restaurant",
            "phone": "+92 42 111 222",
            "email": "hello@zamzam.example",
            "opening_hours": "Mo-Su 11:00-23:00",
            "addr:housenumber": "12",
            "addr:street": "Food Street",
            "addr:city": "Lahore",
            "addr:postcode": "54000",
            "contact:facebook": "https://facebook.com/zamzam",
            "description": "Family-run since 1984",
        },
    },
    {
        "type": "way",
        "id": 202,
        "center": {"lat": 31.5301, "lon": 74.3612},
        "tags": {
            "name": "Aisha Boutique",
            "shop": "clothes",
            "contact:website": "https://aisha.example",
            "contact:phone": "+92 300 1234567",
            "addr:street": "MM Alam Road",
            "addr:city": "Lahore",
        },
    },
    {
        "type": "node",
        "id": 101,
        "lat": 31.5204,
        "lon": 74.3587,
        "tags": {
            "name": "Zam Zam Restaurant",
            "amenity": "restaurant",
            "contact:instagram": "zamzamlahore",
        },
    },
    {
        "type": "node",
        "id": 303,
        "lat": 31.5402,
        "lon": 74.3701,
        "tags": {
            "name": "Regal Hotel",
            "tourism": "hotel",
            "phone": "+92 42 999 000",
            "website": "https://regal.example",
        },
    },
    {
        "type": "node",
        "id": 404,
        "lat": 31.5506,
        "lon": 74.3299,
        "tags": {
            "name": "Iqbal Law Office",
            "office": "lawyer",
            "email": "office@iqbal.example",
            "contact:phone": "+92 42 555 444",
            "note": "Ask for the second floor",
        },
    },
    {
        "type": "node",
        "id": 505,
        "lat": 31.5108,
        "lon": 74.3444,
        "tags": {"name": "Cafe Somewhere", "amenity": "cafe", "website": "no"},
    },
    {
        "type": "node",
        "id": 606,
        "lat": 31.5108,
        "lon": 74.3445,
        "tags": {"amenity": "cafe"},
    },
    {"type": "node", "id": 707, "lat": 31.5, "lon": 74.3, "tags": "not-a-dict"},
    {
        "type": "relation",
        "id": 808,
        "tags": {"name": "Lost Hotel", "tourism": "hotel"},
    },
]


def test_build_query_uses_overpass_bbox_order_and_category_filter():
    """The query receives south,west,north,east and only cafe filters."""
    query = build_query((31.3976, 74.2467, 31.6359, 74.4586), "cafe")

    assert query.startswith("[out:json][timeout:60];")
    assert query.endswith("out center tags;")
    assert "(31.397600,74.246700,31.635900,74.458600)" in query
    assert 'nwr["name"]["amenity"~"^(cafe|ice_cream)$"]' in query
    assert '"shop"' not in query


def test_build_query_all_includes_broad_tag_groups():
    """The all category searches shops, amenities, offices, craft and more."""
    query = build_query((1.0, 2.0, 3.0, 4.0), "all")

    for tag in ("shop", "amenity", "office", "craft", "healthcare", "leisure", "tourism"):
        assert f'["{tag}"' in query


def test_parse_elements_maps_fields_and_deduplicates():
    """Elements map to business fields and duplicates merge into one row."""
    businesses = parse_elements(SAMPLE_ELEMENTS)

    assert len(businesses) == 5
    restaurant = businesses[0]
    assert restaurant.name == "Zam Zam Restaurant"
    assert restaurant.category == "Restaurant"
    assert restaurant.phone == "+92 42 111 222"
    assert restaurant.email == "hello@zamzam.example"
    assert restaurant.address == "12 Food Street, Lahore, 54000"
    assert restaurant.opening_hours == "Mo-Su 11:00-23:00"
    assert restaurant.description == "Family-run since 1984"
    assert restaurant.socials == {
        "Facebook": "https://facebook.com/zamzam",
        "Instagram": "zamzamlahore",
    }
    assert restaurant.has_website is False
    assert restaurant.osm_url == "https://www.openstreetmap.org/node/101"

    boutique = businesses[1]
    assert boutique.category == "Clothing"
    assert boutique.has_website is True
    assert boutique.website == "https://aisha.example"
    assert boutique.address == "MM Alam Road, Lahore"


def test_parse_elements_handles_way_centers_and_missing_names():
    """Way centers are used, nameless and coordinate-less elements are skipped."""
    businesses = parse_elements(SAMPLE_ELEMENTS)
    names = [business.name for business in businesses]

    assert "Aisha Boutique" in names
    assert "Lost Hotel" not in names
    assert None not in names


def test_select_results_defaults_to_businesses_without_websites():
    """The default filter drops websites and puts contactable rows first."""
    results = select_results(parse_elements(SAMPLE_ELEMENTS))

    assert [business.name for business in results] == [
        "Iqbal Law Office",
        "Zam Zam Restaurant",
        "Cafe Somewhere",
    ]


def test_select_results_can_include_every_business():
    """Turning the filter off keeps websites while preserving sort order."""
    results = select_results(
        parse_elements(SAMPLE_ELEMENTS), only_without_website=False
    )

    assert [business.name for business in results] == [
        "Aisha Boutique",
        "Iqbal Law Office",
        "Regal Hotel",
        "Zam Zam Restaurant",
        "Cafe Somewhere",
    ]


def test_select_results_respects_limit():
    """The limit caps the number of returned rows."""
    results = select_results(
        parse_elements(SAMPLE_ELEMENTS), only_without_website=False, limit=2
    )

    assert len(results) == 2
