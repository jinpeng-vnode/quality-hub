"""backend/app/routers/reports.py — 报告看板数据 API

端点: GET /reports/dashboard, GET /reports/trend
"""
from __future__ import annotations

from fastapi import APIRouter, Query
from loguru import logger

from app.database import get_db
from app.models.schemas import (
    DashboardOut, CoverageReport, PassRateReport, TrendPoint,
)

router = APIRouter(tags=["reports"])


@router.get("/reports/dashboard", response_model=DashboardOut)
async def get_dashboard(project_id: str = Query(..., alias="projectId")):
    """获取项目看板数据"""
    db = await get_db()
    try:
        # 覆盖率
        total_features = (await (await db.execute(
            "SELECT COUNT(*) as c FROM features WHERE project_id = ?", (project_id,)
        )).fetchone())["c"]
        covered_features = (await (await db.execute(
            "SELECT COUNT(*) as c FROM features WHERE project_id = ? AND status = 'covered'", (project_id,)
        )).fetchone())["c"]
        coverage_rate = round(covered_features / total_features, 4) if total_features > 0 else 0.0

        # 通过率
        total_runs = (await (await db.execute(
            "SELECT COUNT(*) as c FROM runs WHERE project_id = ?", (project_id,)
        )).fetchone())["c"]
        passed_runs = (await (await db.execute(
            "SELECT COUNT(*) as c FROM runs WHERE project_id = ? AND status = 'passed'", (project_id,)
        )).fetchone())["c"]
        pass_rate = round(passed_runs / total_runs, 4) if total_runs > 0 else 0.0

        # 趋势（最近7天）
        trend = await _get_trend(db, project_id, 7)

        return DashboardOut(
            coverage=CoverageReport(
                projectId=project_id, totalFeatures=total_features,
                coveredFeatures=covered_features, coverageRate=coverage_rate,
            ),
            passRate=PassRateReport(
                projectId=project_id, totalRuns=total_runs,
                passedRuns=passed_runs, passRate=pass_rate,
            ),
            trend=trend,
        )
    finally:
        await db.close()


@router.get("/reports/trend", response_model=list[TrendPoint])
async def get_trend(
    project_id: str = Query(..., alias="projectId"),
    days: int = Query(7, ge=1, le=90),
):
    """获取趋势数据"""
    db = await get_db()
    try:
        return await _get_trend(db, project_id, days)
    finally:
        await db.close()


async def _get_trend(db, project_id: str, days: int) -> list[TrendPoint]:
    """查询指定天数内每天的通过率和用例总数"""
    cursor = await db.execute(
        """
        SELECT date(created_at) as d,
               SUM(passed) as p,
               SUM(total) as t
        FROM runs
        WHERE project_id = ?
          AND created_at >= datetime('now', ?)
        GROUP BY date(created_at)
        ORDER BY d
        """,
        (project_id, f"-{days} days"),
    )
    rows = await cursor.fetchall()
    return [
        TrendPoint(
            date=r["d"],
            passRate=round(r["p"] / r["t"], 4) if r["t"] > 0 else 0.0,
            totalCases=r["t"],
        )
        for r in rows
    ]
