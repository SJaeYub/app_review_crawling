from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Store = Literal["google", "apple"]


class SearchResult(BaseModel):
    store: Store
    app_id: str
    title: Optional[str] = None
    developer: Optional[str] = None
    icon: Optional[str] = None
    score: Optional[float] = None


class Target(BaseModel):
    store: Store
    app_id: str
    country: str = "kr"
    title: Optional[str] = None  # 프론트엔드 표시용(선택)

    @field_validator("country")
    @classmethod
    def _lower_country(cls, v: str) -> str:
        return v.strip().lower()


class ReviewsRequest(BaseModel):
    targets: list[Target] = Field(..., min_length=1)
    start_date: date
    end_date: date
    lang: str = "ko"

    @field_validator("end_date")
    @classmethod
    def _check_range(cls, end_date: date, info):
        start_date = info.data.get("start_date")
        if start_date and end_date < start_date:
            raise ValueError("종료일은 시작일보다 빠를 수 없습니다.")
        return end_date


class ReviewItem(BaseModel):
    store: Store
    author: Optional[str] = None
    rating: Optional[int] = None
    title: Optional[str] = None
    content: Optional[str] = None
    date: str
    app_version: Optional[str] = None


class RatingSummary(BaseModel):
    count: int
    average_rating: Optional[float] = None
    distribution: dict[str, int]
    daily: list[dict]


class StoreResult(BaseModel):
    store: Store
    app_id: str
    country: str
    app_meta: dict
    summary: RatingSummary
    reviews: list[ReviewItem]
    truncated: bool = False
    error: Optional[str] = None


class ReviewsResponse(BaseModel):
    start_date: date
    end_date: date
    results: list[StoreResult]


class ExportRequest(BaseModel):
    format: Literal["csv", "xlsx"]
    results: list[StoreResult]
    filename: Optional[str] = None
