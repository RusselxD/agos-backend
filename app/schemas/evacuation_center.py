from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

EvacuationCenterStatusLiteral = Literal["open", "full", "closed"]


class EvacuationCenterBase(BaseModel):
    location_id: int
    name: str = Field(min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    latitude: float
    longitude: float
    capacity: int | None = None
    contact: str | None = None
    status: EvacuationCenterStatusLiteral = "open"

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError("latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError("longitude must be between -180 and 180")
        return v

    @field_validator("capacity")
    @classmethod
    def validate_capacity(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("capacity cannot be negative")
        return v


class EvacuationCenterCreate(EvacuationCenterBase):
    pass


class EvacuationCenterUpdate(BaseModel):
    """All fields optional so admins can flip status without resending everything."""
    name: str | None = Field(default=None, min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    latitude: float | None = None
    longitude: float | None = None
    capacity: int | None = None
    contact: str | None = None
    status: EvacuationCenterStatusLiteral | None = None

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: float | None) -> float | None:
        if v is not None and not -90 <= v <= 90:
            raise ValueError("latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: float | None) -> float | None:
        if v is not None and not -180 <= v <= 180:
            raise ValueError("longitude must be between -180 and 180")
        return v

    @field_validator("capacity")
    @classmethod
    def validate_capacity(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("capacity cannot be negative")
        return v


class EvacuationCenterResponse(EvacuationCenterBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
