"""backend/app/routers/dashboard.py — 报告看板数据 API"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from loguru import logger

from app.database import get_db
from app.models.schemas import DashboardOut, RunOut

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard():
    """获取看板汇总数据"""
    db = await get_db()
    try:
        total_projects = (await (await db.execute("SELECT COUNT(*) as c FROM projects")).fetchone())["c"]
        total_features = (await (await db.execute("SELECT COUNT(*) as c FROM features")).fetchone())["c"]
        total_cases = (await (await db.execute("SELECT COUNT(*) as c FROM cases")).fetchone())["c"]
        total_runs = (await (await db.execute("SELECT COUNT(*) as c FROM runs")).fetchone())["c"]

        # 计算通过率
        row = await (await db.execute(
            "SELECT COALESCE(SUM(passed), 0) as p, COALESCE(SUM(total), 0) as t FROM runs"
        )).fetchone()
        pass_rate = round(row["p"] / row["t"] * 100, 2) if row["t"] > 0 else 0.0

        # 最近 10 次执行
        cursor = await db.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT 10")
        recent = await cursor.fetchall()

        return DashboardOut(
            totalProjects=total_projects,
            totalFeatures=total_features,
            totalCases=total_cases,
            totalRuns=total_runs,
            passRate=pass_rate,
            recentRuns=[
                RunOut(
                    id=r["id"], projectId=r["project_id"], status=r["status"],
                    total=r["total"], passed=r["passed"], failed=r["failed"], skipped=r["skipped"],
                    startedAt=r["started_at"], finishedAt=r["finished_at"], createdAt=r["created_at"],
                )
                for r in recent
            ],
        )
    except Exception as e:
        logger.error(f"获取看板数据失败: {e}")
        raise HTTPException(status_code=500, detail="获取看板数据失败")
    finally:
        await db.close()
