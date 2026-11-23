"""Pydantic request and response models for the AutoLead API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class SearchRequest(BaseModel):
    """A search for businesses in a named place."""

    location: str = Field(min_length=2, max_length=120)
    category: str = Field(default="all", max_length=40)
    only_without_website: bool = True
    limit: int = Field(default=200, ge=1, le=500)

    @field_validator("location")
    @classmethod
    def normalise_location(cls, value: str) -> str:
        """Collapse whitespace and enforce a useful location length."""
        clean = " ".join(value.split())
        if not 2 <= len(clean) <= 120:
            raise ValueError("Location must be between 2 and 120 characters.")
        return clean

    @field_validator("category")
    @classmethod
    def normalise_category(cls, value: str) -> str:
        """Normalise the category key to lowercase."""
        return value.strip().lower()


class Business(BaseModel):
    """A local business assembled from an OpenStreetMap element."""

    name: str
    category: str
    description: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    opening_hours: str | None = None
    socials: dict[str, str] = Field(default_factory=dict)
    website: str | None = None
    has_website: bool = False
    osm_url: str


class SearchResponse(BaseModel):
    """A complete search result, including the resolved place and bounds."""

    location_resolved: str
    bbox: list[float]
    count: int
    results: list[Business]
    attribution: str = "Data © OpenStreetMap contributors (ODbL)"


class ErrorResponse(BaseModel):
    """A friendly error returned as ``{"error": "..."}``."""

    error: str
