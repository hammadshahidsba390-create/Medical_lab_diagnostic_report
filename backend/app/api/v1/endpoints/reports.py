import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import AppError
from app.db.session import get_db
from app.models.report import Report
from app.models.user import User
from app.normalizer import match_biomarker
from app.rules import flag_value, parse_reference_range
from app.schemas.analysis import (
    CreateReportRequest,
    ReportResponse,
    ResultRow,
    Summary,
)

DISCLAIMER = (
    "This tool is for education only. It does not diagnose, treat or replace advice from "
    "your doctor. Reference ranges differ between laboratories; always discuss your results "
    "with a qualified healthcare professional."
)

router = APIRouter(prefix="/reports", tags=["reports"])


def _evaluate_rows(rows: list[Any]) -> tuple[list[ResultRow], Summary]:
    results: list[ResultRow] = []
    for row in rows:
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

    counts = {
        f: sum(r.flag == f for r in results)
        for f in ("low", "normal", "high", "unknown")
    }
    summary = Summary(
        total=len(results),
        unmatched=sum(r.biomarker_id is None for r in results),
        **counts,
    )
    return results, summary


@router.post(
    "",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze and persist a lab diagnostic report (Vertical Slice)",
)
def create_report(
    req: CreateReportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    results, summary = _evaluate_rows(req.rows)

    report = Report(
        user_id=user.id,
        title=req.title,
        results=[r.model_dump() for r in results],
        summary=summary.model_dump(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return ReportResponse(
        id=str(report.id),
        user_id=str(report.user_id),
        title=report.title,
        results=results,
        summary=summary,
        created_at=report.created_at.isoformat(),
        disclaimer=DISCLAIMER,
    )


@router.get(
    "",
    response_model=list[ReportResponse],
    summary="List current user's saved lab reports",
)
def list_reports(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReportResponse]:
    stmt = (
        select(Report)
        .where(Report.user_id == user.id)
        .order_by(Report.created_at.desc())
    )
    reports = db.scalars(stmt).all()
    return [
        ReportResponse(
            id=str(r.id),
            user_id=str(r.user_id),
            title=r.title,
            results=[ResultRow(**row) for row in r.results],
            summary=Summary(**r.summary),
            created_at=r.created_at.isoformat(),
            disclaimer=DISCLAIMER,
        )
        for r in reports
    ]


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Get single report with tenant isolation",
)
def get_report(
    report_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportResponse:
    report = db.get(Report, report_id)
    if report is None or (report.user_id != user.id and user.role != "admin"):
        raise AppError(404, "not_found", "Report not found.")

    return ReportResponse(
        id=str(report.id),
        user_id=str(report.user_id),
        title=report.title,
        results=[ResultRow(**row) for row in report.results],
        summary=Summary(**report.summary),
        created_at=report.created_at.isoformat(),
        disclaimer=DISCLAIMER,
    )


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved report",
)
def delete_report(
    report_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    report = db.get(Report, report_id)
    if report is None or (report.user_id != user.id and user.role != "admin"):
        raise AppError(404, "not_found", "Report not found.")

    db.delete(report)
    db.commit()

