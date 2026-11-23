"""FastAPI application, API routes, and static frontend serving."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .categories import CATEGORIES_BY_KEY, category_options
from .geo import GeocodeError, LocationNotFound, geocode
from .models import ErrorResponse, SearchRequest, SearchResponse
from .overpass import OverpassError, search_businesses

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="AutoLead",
    version="0.1.0",
    description="Find local businesses without a website using OpenStreetMap.",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_request, exc: RequestValidationError) -> JSONResponse:
    """Return friendly 400 responses for invalid search input."""
    message = "Check the search fields and try again."
    for error in exc.errors():
        if "location" in error.get("loc", ()):
            message = "Enter a location between 2 and 120 characters."
            break
    return JSONResponse(status_code=400, content={"error": message})


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """Serve the single-page frontend."""
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Report that the application is running."""
    return {"status": "ok"}


@app.get("/api/categories")
async def categories() -> list[dict[str, str]]:
    """Return the categories available in the search dropdown."""
    return category_options()


@app.post(
    "/api/search",
    response_model=SearchResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
    },
)
async def search(payload: SearchRequest) -> SearchResponse | JSONResponse:
    """Find businesses in a place and return their contact details."""
    if payload.category not in CATEGORIES_BY_KEY:
        return JSONResponse(
            status_code=400,
            content={"error": "Unknown category. Choose one from the category list."},
        )

    try:
        place = await geocode(payload.location)
    except LocationNotFound as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})
    except GeocodeError as exc:
        return JSONResponse(status_code=502, content={"error": str(exc)})

    try:
        results = await search_businesses(
            bbox=place.bbox,
            category=payload.category,
            only_without_website=payload.only_without_website,
            limit=payload.limit,
        )
    except OverpassError as exc:
        return JSONResponse(status_code=502, content={"error": str(exc)})

    return SearchResponse(
        location_resolved=place.display_name,
        bbox=list(place.bbox),
        count=len(results),
        results=results,
    )
