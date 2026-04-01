"""Pydantic response models for property lookup."""

from pydantic import BaseModel


class CoreFields(BaseModel):
    beds: int | None = None
    baths: int | None = None
    half_baths: int | None = None
    sqft: int | None = None
    lot_sqft: int | None = None
    year_built: int | None = None


class DetailFields(BaseModel):
    property_type: str | None = None
    stories: int | None = None
    garage_spaces: int | None = None
    has_pool: bool | None = None
    has_basement: bool | None = None
    heating_type: str | None = None
    cooling_type: str | None = None
    roof_type: str | None = None
    hoa_monthly: float | None = None


class Amenity(BaseModel):
    name: str
    type: str
    distance_mi: float


class SchoolRating(BaseModel):
    name: str
    rating: int | None = None


class SchoolRatings(BaseModel):
    elementary: SchoolRating | None = None
    middle: SchoolRating | None = None
    high: SchoolRating | None = None


class NeighborhoodFields(BaseModel):
    walk_score: int | None = None
    transit_score: int | None = None
    bike_score: int | None = None
    nearby_amenities: list[Amenity] = []
    school_ratings: SchoolRatings | None = None
    lifestyle_tags: list[str] = []


class PropertyLookupResponse(BaseModel):
    source: str
    found: bool
    core: CoreFields = CoreFields()
    details: DetailFields = DetailFields()
    neighborhood: NeighborhoodFields = NeighborhoodFields()
