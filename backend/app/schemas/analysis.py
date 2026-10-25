"""Pydantic models for the API. Every pipeline stage exchanges typed objects."""
from typing import Literal

from pydantic import BaseModel, Field

Flag = Literal["low", "normal", "high", "unknown"]


class ExtractedRow(BaseModel):
    """One test line as read from a report (by OCR/LLM or typed by the user)."""

    raw_name: str = Field(min_length=1, max_length=120)
    value: float | str
    unit: str | None = Field(default=None, max_length=30)
    reference_range: str | None = Field(default=None, max_length=60)


class AnalyzeRequest(BaseModel):
    rows: list[ExtractedRow] = Field(min_length=1, max_length=200)


class ResultRow(BaseModel):
    raw_name: str
    biomarker_id: str | None
    biomarker_name: str | None
    match_score: float
    value: float | str
    unit: str | None
    reference_range: str | None
    range_source: Literal["report", "unavailable"]
    flag: Flag


class Summary(BaseModel):
    total: int
    low: int
    normal: int
    high: int
    unknown: int
    unmatched: int


class AnalyzeResponse(BaseModel):
    results: list[ResultRow]
    summary: Summary
    disclaimer: str
