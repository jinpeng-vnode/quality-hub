"""backend/app/routers/runs.py — 执行管理 API + Midscene 集成"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.database import get_db
from app.models.schemas import RunCreate, RunOut, RunReportOut, RunResultOut

router = APIRouter(tags=["runs"])


@router.post("/runs", response_model=RunOut)
async def create_run(body: RunCreate):
    """创建执行记录并触发测试运行"""
    db = await get_db()
    try:
        # 校验项目存在
        cursor = await db.execute("SELECT id FROM projects WHERE id = ?", (body.project_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        # 获取要执行的用例
        if body.case_ids:
            placeholders = ",".join("?" * len(body.case_ids))
            cursor = await db.execute(f"SELECT id FROM cases WHERE id IN ({placeholders})", body.case_ids)
        else:
            # 未指定用例时，执行项目下所有用例
            cursor = await db.execute(
                "SELECT c.id FROM cases c JOIN features f ON c.feature_id = f.id WHERE f.project_id = ?",
                (body.project_id,),
            )
        case_rows = await cursor.fetchall()
        case_ids = [r["id"] for r in case_rows]

        run_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO runs (id, project_id, status, total, started_at) VALUES (?, ?, ?, ?, ?)",
            (run_id, body.project_id, "running", len(case_ids), now),
        )

        # 创建每条用例的执行结果记录
        for cid in case_ids:
            await db.execute(
                "INSERT INTO run_results (id, run_id, case_id, status) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), run_id, cid, "pending"),
            )

        await db.commit()

        # TODO: 等待集成测试 — 调用 Midscene.js 执行 E2E 测试
        # 实际执行逻辑：通过 subprocess 调用 node 脚本，异步更新 run_results
        # 暂时将所有结果标记为 skipped
        await _mark_run_complete(db, run_id, case_ids)

        cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = await cursor.fetchone()
        logger.info(f"创建执行记录: {run_id} (用例数={len(case_ids)})")
        return _row_to_run(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建执行记录失败: {e}")
        raise HTTPException(status_code=500, detail="创建执行记录失败")
    finally:
        await db.close()


async def _mark_run_complete(db, run_id: str, case_ids: list[str]) -> None:
    """临时：将执行标记为完成（Midscene 集成前的占位逻辑）"""
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        "UPDATE run_results SET status = 'skipped' WHERE run_id = ?",
        (run_id,),
    )
    await db.execute(
        "UPDATE runs SET status = 'completed', skipped = ?, finished_at = ? WHERE id = ?",
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
        rows = await cursor.fetchall()
        return [_row_to_run(r) for r in rows]
    except Exception as e:
        logger.error(f"获取执行记录列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取执行记录列表失败")
    finally:
        await db.close()


@router.get("/runs/{run_id}/report", response_model=RunReportOut)
async def get_run_report(run_id: str):
    """获取执行报告详情"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        run_row = await cursor.fetchone()
        if not run_row:
            raise HTTPException(status_code=404, detail="执行记录不存在")

        cursor = await db.execute("SELECT * FROM run_results WHERE run_id = ?", (run_id,))
        result_rows = await cursor.fetchall()

        return RunReportOut(
            run=_row_to_run(run_row),
            results=[
                RunResultOut(
                    id=r["id"], caseId=r["case_id"], status=r["status"],
                    errorMessage=r["error_message"], durationMs=r["duration_ms"],
                )
                for r in result_rows
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取执行报告失败: {e}")
        raise HTTPException(status_code=500, detail="获取执行报告失败")
    finally:
        await db.close()


def _row_to_run(r) -> RunOut:
    return RunOut(
        id=r["id"], projectId=r["project_id"], status=r["status"],
        total=r["total"], passed=r["passed"], failed=r["failed"], skipped=r["skipped"],
        startedAt=r["started_at"], finishedAt=r["finished_at"], createdAt=r["created_at"],
    )
