"""backend/app/routers/runs.py — 执行管理 API

端点: POST/GET /runs, GET /runs/{id}, GET /runs/{id}/results, PUT /runs/{id}/results/{result_id}
"""
from __future__ import annotations

import asyncio
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Query
from loguru import logger

from app.database import get_db
from app.models.schemas import RunCreate, RunOut, RunResultOut, RunResultUpdate
from app.utils.exceptions import NotFoundException, ForbiddenException

router = APIRouter(tags=["runs"])


def _row_to_run(r) -> RunOut:
    return RunOut(
        id=r["id"], projectId=r["project_id"], status=r["status"],
        mode=r["mode"] if "mode" in r.keys() else "manual",
        total=r["total"], passed=r["passed"], failed=r["failed"],
        skipped=r["skipped"] if "skipped" in r.keys() else 0,
        startedAt=r["started_at"], finishedAt=r["finished_at"], createdAt=r["created_at"],
    )


def _row_to_result(r) -> RunResultOut:
    return RunResultOut(
        id=r["id"], runId=r["run_id"], caseId=r["case_id"],
        status=r["status"], errorMessage=r["error_message"] or None,
        durationMs=r["duration_ms"],
        log=r["log"] if "log" in r.keys() else "",
    )


@router.post("/runs", response_model=RunOut)
async def create_run(body: RunCreate):
    """创建执行记录，mode=manual等待手动标记，mode=script后台执行脚本"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM projects WHERE id = ?", (body.project_id,))
        if not await cursor.fetchone():
            raise NotFoundException("项目不存在")

        # 获取要执行的用例
        if body.case_ids:
            placeholders = ",".join("?" * len(body.case_ids))
            cursor = await db.execute(f"SELECT id, midscene_script FROM cases WHERE id IN ({placeholders})", body.case_ids)
        else:
            cursor = await db.execute(
                "SELECT c.id, c.midscene_script FROM cases c JOIN features f ON c.feature_id = f.id WHERE f.project_id = ?",
                (body.project_id,),
            )
        cases = [dict(r) for r in await cursor.fetchall()]

        run_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO runs (id, project_id, status, mode, total, started_at) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, body.project_id, "running", body.mode, len(cases), now),
        )

        # 创建每条用例的执行结果记录
        case_scripts = []
        for c in cases:
            result_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO run_results (id, run_id, case_id, status) VALUES (?, ?, ?, ?)",
                (result_id, run_id, c["id"], "pending"),
            )
            case_scripts.append({"result_id": result_id, "script": c.get("midscene_script") or ""})
        await db.commit()

        # script模式：后台异步执行
        if body.mode == "script":
            asyncio.create_task(_execute_script_run(run_id, case_scripts))

        cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = await cursor.fetchone()
        logger.info(f"创建执行记录: {run_id} (mode={body.mode}, 用例数={len(cases)})")
        return _row_to_run(row)
    finally:
        await db.close()


@router.put("/runs/{run_id}/results/{result_id}", response_model=RunResultOut)
async def update_run_result(run_id: str, result_id: str, body: RunResultUpdate):
    """手动标记单条执行结果（仅manual模式）"""
    db = await get_db()
    try:
        # 检查run存在且为manual模式
        cursor = await db.execute("SELECT mode FROM runs WHERE id = ?", (run_id,))
        run_row = await cursor.fetchone()
        if not run_row:
            raise NotFoundException("执行记录不存在")
        if run_row["mode"] != "manual":
            raise ForbiddenException("仅手动模式可标记结果")

        # 检查result存在
        cursor = await db.execute("SELECT id FROM run_results WHERE id = ? AND run_id = ?", (result_id, run_id))
        if not await cursor.fetchone():
            raise NotFoundException("执行结果不存在")

        # 更新result
        await db.execute(
            "UPDATE run_results SET status = ?, error_message = ?, duration_ms = ? WHERE id = ?",
            (body.status, body.error_message, body.duration_ms, result_id),
        )
        await db.commit()

        # 重新计算run统计
        await _recalculate_run(db, run_id)

        cursor = await db.execute("SELECT * FROM run_results WHERE id = ?", (result_id,))
        return _row_to_result(await cursor.fetchone())
    finally:
        await db.close()


@router.get("/runs", response_model=list[RunOut])
async def list_runs(project_id: str = Query(..., alias="projectId")):
    """获取执行记录列表"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM runs WHERE project_id = ? ORDER BY created_at DESC", (project_id,),
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


@router.delete("/runs/{run_id}")
async def delete_run(run_id: str):
    """删除执行记录（级联删除关联的 run_results）"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM runs WHERE id = ?", (run_id,))
        if not await cursor.fetchone():
            raise NotFoundException(f"未找到 ID 为 {run_id} 的执行记录")
        await db.execute("DELETE FROM run_results WHERE run_id = ?", (run_id,))
        await db.execute("DELETE FROM runs WHERE id = ?", (run_id,))
        await db.commit()
        logger.info(f"删除执行记录: {run_id}")
        return {"ok": True}
    finally:
        await db.close()


@router.post("/runs/{run_id}/cancel", response_model=RunOut)
async def cancel_run(run_id: str):
    """取消执行中的 run，将 running 改为 error，pending 的 results 改为 skipped"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = await cursor.fetchone()
        if not row:
            raise NotFoundException("执行记录不存在")
        if row["status"] != "running":
            raise ForbiddenException("仅执行中的记录可取消")

        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "UPDATE run_results SET status = 'skipped' WHERE run_id = ? AND status = 'pending'",
            (run_id,),
        )
        # 重新统计
        cursor = await db.execute("SELECT status FROM run_results WHERE run_id = ?", (run_id,))
        rows = await cursor.fetchall()
        passed = sum(1 for r in rows if r["status"] == "passed")
        failed = sum(1 for r in rows if r["status"] == "failed")
        skipped = sum(1 for r in rows if r["status"] == "skipped")
        await db.execute(
            "UPDATE runs SET status = 'error', passed = ?, failed = ?, skipped = ?, finished_at = ? WHERE id = ?",
            (passed, failed, skipped, now, run_id),
        )
        await db.commit()
        logger.info(f"取消执行记录: {run_id}")
        cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        return _row_to_run(await cursor.fetchone())
    finally:
        await db.close()


@router.get("/runs/{run_id}/results", response_model=list[RunResultOut])
async def get_run_results(run_id: str):
    """获取执行结果明细（含用例标题和功能点信息）"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM runs WHERE id = ?", (run_id,))
        if not await cursor.fetchone():
            raise NotFoundException(f"未找到 ID 为 {run_id} 的执行记录")
        cursor = await db.execute(
            """SELECT rr.*, c.title as case_title, c.feature_id, f.title as feature_title
               FROM run_results rr
               LEFT JOIN cases c ON rr.case_id = c.id
               LEFT JOIN features f ON c.feature_id = f.id
               WHERE rr.run_id = ?
               ORDER BY f.title, c.title""",
            (run_id,),
        )
        results = []
        for r in await cursor.fetchall():
            results.append(RunResultOut(
                id=r["id"], runId=r["run_id"], caseId=r["case_id"],
                caseTitle=r["case_title"] or "",
                featureId=r["feature_id"] or "",
                featureTitle=r["feature_title"] or "未分类",
                status=r["status"], errorMessage=r["error_message"] or None,
                durationMs=r["duration_ms"],
                log=r["log"] if "log" in r.keys() else "",
            ))
        return results
    finally:
        await db.close()


@router.get("/runs/{run_id}/report")
async def get_run_report(run_id: str):
    """获取单次执行的统计报告（通过数、失败数、跳过数、通过率、按功能点分组）"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = await cursor.fetchone()
        if not row:
            raise NotFoundException("执行记录不存在")

        cursor = await db.execute(
            """SELECT rr.status, f.title as feature_title
               FROM run_results rr
               LEFT JOIN cases c ON rr.case_id = c.id
               LEFT JOIN features f ON c.feature_id = f.id
               WHERE rr.run_id = ?""",
            (run_id,),
        )
        results = await cursor.fetchall()
        passed = sum(1 for r in results if r["status"] == "passed")
        failed = sum(1 for r in results if r["status"] == "failed")
        skipped = sum(1 for r in results if r["status"] == "skipped")
        total = len(results)
        pass_rate = round(passed / total * 100, 1) if total > 0 else 0.0

        # 按功能点分组统计
        groups: dict[str, dict] = {}
        for r in results:
            ft = r["feature_title"] or "未分类"
            if ft not in groups:
                groups[ft] = {"featureTitle": ft, "passed": 0, "failed": 0, "skipped": 0, "total": 0}
            groups[ft]["total"] += 1
            if r["status"] in ("passed", "failed", "skipped"):
                groups[ft][r["status"]] += 1

        return {
            "runId": run_id,
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "passRate": pass_rate,
            "groups": list(groups.values()),
        }
    finally:
        await db.close()


# === 脚本执行引擎 ===

async def _execute_script_run(run_id: str, case_scripts: list[dict]) -> None:
    """后台执行脚本任务，串行处理每条用例"""
    db = await get_db()
    try:
        for item in case_scripts:
            result_id = item["result_id"]
            script = item["script"]

            if not script:
                await db.execute(
                    "UPDATE run_results SET status = 'skipped' WHERE id = ?", (result_id,),
                )
                await db.commit()
                continue

            start = datetime.now(timezone.utc)
            status, log = await _run_single_script(script)
            duration = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
            error_msg = log if status == "failed" else ""
            await db.execute(
                "UPDATE run_results SET status = ?, error_message = ?, duration_ms = ?, log = ? WHERE id = ?",
                (status, error_msg, duration, log, result_id),
            )
            await db.commit()

        # 更新run汇总
        await _recalculate_run(db, run_id)
    except Exception as e:
        logger.error(f"脚本执行异常 run={run_id}: {e}")
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "UPDATE runs SET status = 'error', finished_at = ? WHERE id = ?", (now, run_id),
        )
        await db.commit()
    finally:
        await db.close()


async def _run_single_script(script: str) -> tuple[str, str]:
    """执行单条脚本，返回 (status, log)"""
    tmp_dir = tempfile.mkdtemp(prefix="qh_run_")
    script_path = Path(tmp_dir) / "test_script.py"
    try:
        script_path.write_text(script, encoding="utf-8")
        proc = await asyncio.create_subprocess_exec(
            "python3", str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tmp_dir,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        log = (stdout.decode() + "\n" + stderr.decode()).strip()
        status = "passed" if proc.returncode == 0 else "failed"
        return status, log
    except asyncio.TimeoutError:
        proc.kill()  # type: ignore
        return "failed", "执行超时（15s）"
    except Exception as e:
        return "failed", f"执行异常: {e}"
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


async def _recalculate_run(db, run_id: str) -> None:
    """重新计算run的统计数据，检查是否全部完成"""
    cursor = await db.execute("SELECT status FROM run_results WHERE run_id = ?", (run_id,))
    rows = await cursor.fetchall()
    passed = sum(1 for r in rows if r["status"] == "passed")
    failed = sum(1 for r in rows if r["status"] == "failed")
    skipped = sum(1 for r in rows if r["status"] == "skipped")
    pending = sum(1 for r in rows if r["status"] == "pending")

    now = datetime.now(timezone.utc).isoformat()
    if pending == 0:
        # 全部完成：有失败则 failed，全 skipped 则 completed，否则 passed
        if failed > 0:
            run_status = "failed"
        elif passed == 0 and skipped > 0:
            run_status = "completed"
        else:
            run_status = "passed"
        await db.execute(
            "UPDATE runs SET status = ?, passed = ?, failed = ?, skipped = ?, finished_at = ? WHERE id = ?",
            (run_status, passed, failed, skipped, now, run_id),
        )
    else:
        await db.execute(
            "UPDATE runs SET passed = ?, failed = ?, skipped = ? WHERE id = ?",
            (passed, failed, skipped, run_id),
        )
    await db.commit()
