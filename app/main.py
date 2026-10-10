"""LabReport AI - FastAPI application.

Design rule: abnormal/normal is decided here, in code (rules.py). The AI model is
only ever asked to explain a result that has already been flagged.
"""
from fastapi import FastAPI

from app.normalizer import match_biomarker
from app.rules import flag_value, parse_reference_range
from app.schemas import AnalyzeRequest, AnalyzeResponse, ResultRow, Summary

DISCLAIMER = (
    "This tool is for education only. It does not diagnose, treat or replace advice from "
    "your doctor. Reference ranges differ between laboratories; always discuss your results "
    "with a qualified healthcare professional."
)

app = FastAPI(title="LabReport AI", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


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
