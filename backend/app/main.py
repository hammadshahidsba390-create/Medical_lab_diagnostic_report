"""LabReport AI - FastAPI application.

Design rule: abnormal/normal is decided here, in code (rules.py). The AI model is
only ever asked to explain a result that has already been flagged.
"""
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError, register_error_handlers
from app.db.session import get_db
from app.normalizer import match_biomarker
from app.rules import flag_value, parse_reference_range
from app.schemas.analysis import AnalyzeRequest, AnalyzeResponse, ResultRow, Summary

DISCLAIMER = (
    "This tool is for education only. It does not diagnose, treat or replace advice from "
    "your doctor. Reference ranges differ between laboratories; always discuss your results "
    "with a qualified healthcare professional."
)

app = FastAPI(title="LabReport AI", version="0.2.0")
register_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict:
    """Checks that the database can be reached. Used after setup and by the uptime monitor."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise AppError(503, "database_unavailable", "The database is not reachable.") from None
    return {"status": "ok", "database": "connected"}


@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    results: list[ResultRow] = []
    for row in req.rows:
        match = match_biomarker(row.raw_name)
        low, high = parse_reference_range(row.reference_range or "")
        has_range = low is not None or high is not None
        results.append(
            ResultRow(
                raw_name=row.raw_name,
                biomarker_id=match.biomarker_id,
                biomarker_name=match.biomarker_name,
                match_score=match.score,
                value=row.value,
                unit=row.unit,
                reference_range=row.reference_range,
                range_source="report" if has_range else "unavailable",
                flag=flag_value(row.value, low, high),
            )
        )

    counts = {f: sum(r.flag == f for r in results) for f in ("low", "normal", "high", "unknown")}
    summary = Summary(
        total=len(results),
        unmatched=sum(r.biomarker_id is None for r in results),
        **counts,
    )
    return AnalyzeResponse(results=results, summary=summary, disclaimer=DISCLAIMER)
