"""backend/app/routers/runs.py — 执行管理 API

端点: POST/GET /runs, GET /runs/{id}, GET /runs/{id}/results
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Query
from loguru import logger

from app.database import get_db
from app.models.schemas import RunCreate, RunOut, RunResultOut
from app.utils.exceptions import NotFoundException

router = APIRouter(tags=["runs"])


def _row_to_run(r) -> RunOut:
    return RunOut(
        id=r["id"], projectId=r["project_id"], status=r["status"],
        total=r["total"], passed=r["passed"], failed=r["failed"],
        startedAt=r["started_at"], finishedAt=r["finished_at"], createdAt=r["created_at"],
    )


@router.post("/runs", response_model=RunOut)
async def create_run(body: RunCreate):
    """创建执行记录并触发测试运行"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM projects WHERE id = ?", (body.project_id,))
        if not await cursor.fetchone():
            raise NotFoundException("项目不存在")

        # 获取要执行的用例
        if body.case_ids:
            placeholders = ",".join("?" * len(body.case_ids))
            cursor = await db.execute(f"SELECT id FROM cases WHERE id IN ({placeholders})", body.case_ids)
        else:
            cursor = await db.execute(
                "SELECT c.id FROM cases c JOIN features f ON c.feature_id = f.id WHERE f.project_id = ?",
                (body.project_id,),
            )
        case_ids = [r["id"] for r in await cursor.fetchall()]

        run_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO runs (id, project_id, status, total, env_url, started_at) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, body.project_id, "running", len(case_ids), body.env_url, now),
        )

        # 创建每条用例的执行结果记录
        for cid in case_ids:
            await db.execute(
                "INSERT INTO run_results (id, run_id, case_id, status) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), run_id, cid, "pending"),
            )
        await db.commit()

        # TODO: 等待集成测试 — 调用 Midscene.js 执行 E2E 测试
        await _mark_run_complete(db, run_id, case_ids)

        cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = await cursor.fetchone()
        logger.info(f"创建执行记录: {run_id} (用例数={len(case_ids)})")
        return _row_to_run(row)
    finally:
        await db.close()


async def _mark_run_complete(db, run_id: str, case_ids: list[str]) -> None:
    """临时：将执行标记为完成（Midscene 集成前的占位逻辑）"""
    now = datetime.now(timezone.utc).isoformat()
    await db.execute("UPDATE run_results SET status = 'passed' WHERE run_id = ?", (run_id,))
    await db.execute(
        "UPDATE runs SET status = 'passed', passed = ?, finished_at = ? WHERE id = ?",
        (len(case_ids), now, run_id),
    )
    await db.commit()


@router.get("/runs", response_model=list[RunOut])
async def list_runs(project_id: str = Query(..., alias="projectId")):
    """获取执行记录列表"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM runs WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )
        return [_row_to_run(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


@router.get("/runs/{run_id}", response_model=RunOut)
async def get_run(run_id: str):
    """获取执行详情"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = await cursor.fetchone()
        if not row:
            raise NotFoundException(f"未找到 ID 为 {run_id} 的执行记录")
        return _row_to_run(row)
    finally:
        await db.close()


@router.get("/runs/{run_id}/results", response_model=list[RunResultOut])
async def get_run_results(run_id: str):
    """获取执行结果明细"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM runs WHERE id = ?", (run_id,))
        if not await cursor.fetchone():
            raise NotFoundException(f"未找到 ID 为 {run_id} 的执行记录")

        cursor = await db.execute("SELECT * FROM run_results WHERE run_id = ?", (run_id,))
        rows = await cursor.fetchall()
        return [
            RunResultOut(
                id=r["id"], runId=r["run_id"], caseId=r["case_id"],
                status=r["status"], errorMessage=r["error_message"] or None,
                screenshotUrl=r["screenshot_url"], durationMs=r["duration_ms"],
            )
            for r in rows
        ]
    finally:
        await db.close()
