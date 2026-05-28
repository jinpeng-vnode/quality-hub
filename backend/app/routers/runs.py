"""backend/app/routers/runs.py — 执行管理 API

端点: POST/GET /runs, GET /runs/{id}, GET /runs/{id}/results, PUT /runs/{id}/results/{result_id}
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
import tempfile
import uuid
from datetime import datetime, timezone, timedelta

# 上海时区 UTC+8
_SHANGHAI_TZ = timezone(timedelta(hours=8))
from pathlib import Path

from fastapi import APIRouter, Query
from loguru import logger

from app.database import get_db
from app.models.schemas import RunCreate, RunOut, RunResultOut, RunResultUpdate
from app.utils.exceptions import NotFoundException, ForbiddenException

router = APIRouter(tags=["runs"])

# 图床配置（freeimage.host）
_IMAGE_HOSTING_API = "https://freeimage.host/api/1/upload"
_IMAGE_HOSTING_KEY = "6d207e02198a847aa98d0a2a901485a5"


def _row_to_run(r) -> RunOut:
    return RunOut(
        id=r["id"], projectId=r["project_id"], status=r["status"],
        mode=r["mode"] if "mode" in r.keys() else "manual",
        total=r["total"], passed=r["passed"], failed=r["failed"],
        skipped=r["skipped"] if "skipped" in r.keys() else 0,
        startedAt=r["started_at"], finishedAt=r["finished_at"], createdAt=r["created_at"],
    )


def _row_to_result(r) -> RunResultOut:
    screenshots_raw = r["screenshots"] if "screenshots" in r.keys() else "[]"
    try:
        screenshots = json.loads(screenshots_raw) if screenshots_raw else []
    except (json.JSONDecodeError, TypeError):
        screenshots = []
    return RunResultOut(
        id=r["id"], runId=r["run_id"], caseId=r["case_id"],
        status=r["status"], errorMessage=r["error_message"] or None,
        durationMs=r["duration_ms"],
        log=r["log"] if "log" in r.keys() else "",
        screenshots=screenshots,
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
        elif body.feature_ids:
            placeholders = ",".join("?" * len(body.feature_ids))
            cursor = await db.execute(f"SELECT id, midscene_script FROM cases WHERE feature_id IN ({placeholders})", body.feature_ids)
        else:
            cursor = await db.execute(
                "SELECT c.id, c.midscene_script FROM cases c JOIN features f ON c.feature_id = f.id WHERE f.project_id = ?",
                (body.project_id,),
            )
        cases = [dict(r) for r in await cursor.fetchall()]

        run_id = str(uuid.uuid4())
        now = datetime.now(_SHANGHAI_TZ).isoformat()
        await db.execute(
            "INSERT INTO runs (id, project_id, status, mode, total, started_at) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, body.project_id, "running", "script", len(cases), now),
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

        # 后台异步执行脚本
        asyncio.create_task(_execute_script_run(run_id, case_scripts, body.timeout))

        cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        row = await cursor.fetchone()
        logger.info(f"创建执行记录: {run_id} (mode={body.mode}, 用例数={len(cases)})")
        return _row_to_run(row)
    finally:
        await db.close()


@router.put("/runs/{run_id}/results/{result_id}", response_model=RunResultOut)
async def update_run_result(run_id: str, result_id: str, body: RunResultUpdate):
    """手动标记单条执行结果（允许覆盖脚本执行结果）"""
    db = await get_db()
    try:
        # 检查run存在
        cursor = await db.execute("SELECT mode FROM runs WHERE id = ?", (run_id,))
        run_row = await cursor.fetchone()
        if not run_row:
            raise NotFoundException("执行记录不存在")

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

        now = datetime.now(_SHANGHAI_TZ).isoformat()
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


@router.post("/runs/{run_id}/retry/{result_id}", response_model=RunResultOut)
async def retry_single_result(run_id: str, result_id: str):
    """重新执行单条用例"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
        run_row = await cursor.fetchone()
        if not run_row:
            raise NotFoundException("执行记录不存在")

        cursor = await db.execute(
            "SELECT rr.*, c.midscene_script FROM run_results rr JOIN cases c ON rr.case_id = c.id WHERE rr.id = ? AND rr.run_id = ?",
            (result_id, run_id),
        )
        row = await cursor.fetchone()
        if not row:
            raise NotFoundException("执行结果不存在")

        script = row["midscene_script"] or ""
        if not script:
            raise ForbiddenException("该用例无脚本，无法执行")

        # 重置状态为 pending
        await db.execute("UPDATE run_results SET status = 'pending', error_message = '', log = '', screenshots = '[]', duration_ms = 0 WHERE id = ?", (result_id,))
        # 将 run 状态改回 running
        await db.execute("UPDATE runs SET status = 'running', finished_at = NULL WHERE id = ?", (run_id,))
        await db.commit()

        # 后台执行
        asyncio.create_task(_execute_single_retry(run_id, result_id, script, run_row["mode"]))

        cursor = await db.execute(
            """SELECT rr.*, c.title as case_title, c.feature_id, f.title as feature_title
               FROM run_results rr LEFT JOIN cases c ON rr.case_id = c.id LEFT JOIN features f ON c.feature_id = f.id
               WHERE rr.id = ?""", (result_id,))
        r = await cursor.fetchone()
        screenshots_raw = r["screenshots"] if "screenshots" in r.keys() else "[]"
        try:
            screenshots = json.loads(screenshots_raw) if screenshots_raw else []
        except (json.JSONDecodeError, TypeError):
            screenshots = []
        return RunResultOut(
            id=r["id"], runId=r["run_id"], caseId=r["case_id"],
            caseTitle=r["case_title"] or "", featureId=r["feature_id"] or "",
            featureTitle=r["feature_title"] or "未分类",
            status=r["status"], errorMessage=r["error_message"] or None,
            durationMs=r["duration_ms"], log=r["log"] if "log" in r.keys() else "",
            screenshots=screenshots,
        )
    finally:
        await db.close()


async def _execute_single_retry(run_id: str, result_id: str, script: str, mode: str) -> None:
    """后台重试单条用例"""
    db = await get_db()
    try:
        start = datetime.now(_SHANGHAI_TZ)
        status, log, screenshots = await _run_single_script(script, timeout=60)
        duration = int((datetime.now(_SHANGHAI_TZ) - start).total_seconds() * 1000)
        error_msg = log if status == "failed" else ""
        await db.execute(
            "UPDATE run_results SET status = ?, error_message = ?, duration_ms = ?, log = ?, screenshots = ? WHERE id = ?",
            (status, error_msg, duration, log, json.dumps(screenshots), result_id),
        )
        await db.commit()
        await _recalculate_run(db, run_id)
    except Exception as e:
        logger.error(f"重试异常 result={result_id}: {e}")
        await db.execute("UPDATE run_results SET status = 'failed', error_message = ? WHERE id = ?", (str(e), result_id))
        await db.commit()
        await _recalculate_run(db, run_id)
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
            screenshots_raw = r["screenshots"] if "screenshots" in r.keys() else "[]"
            try:
                screenshots = json.loads(screenshots_raw) if screenshots_raw else []
            except (json.JSONDecodeError, TypeError):
                screenshots = []
            results.append(RunResultOut(
                id=r["id"], runId=r["run_id"], caseId=r["case_id"],
                caseTitle=r["case_title"] or "",
                featureId=r["feature_id"] or "",
                featureTitle=r["feature_title"] or "未分类",
                status=r["status"], errorMessage=r["error_message"] or None,
                durationMs=r["duration_ms"],
                log=r["log"] if "log" in r.keys() else "",
                screenshots=screenshots,
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

async def _execute_script_run(run_id: str, case_scripts: list[dict], timeout: int = 60) -> None:
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

            start = datetime.now(_SHANGHAI_TZ)
            status, log, screenshots = await _run_single_script(script, timeout)
            duration = int((datetime.now(_SHANGHAI_TZ) - start).total_seconds() * 1000)
            error_msg = log if status == "failed" else ""
            await db.execute(
                "UPDATE run_results SET status = ?, error_message = ?, duration_ms = ?, log = ?, screenshots = ? WHERE id = ?",
                (status, error_msg, duration, log, json.dumps(screenshots), result_id),
            )
            await db.commit()

        # 更新run汇总
        await _recalculate_run(db, run_id)
    except Exception as e:
        logger.error(f"脚本执行异常 run={run_id}: {e}")
        now = datetime.now(_SHANGHAI_TZ).isoformat()
        await db.execute(
            "UPDATE runs SET status = 'error', finished_at = ? WHERE id = ?", (now, run_id),
        )
        await db.commit()
    finally:
        await db.close()


async def _run_single_script(script: str, timeout: int = 60) -> tuple[str, str, list[str]]:
    """执行单条脚本，返回 (status, log, screenshots)
    自动在脚本末尾注入截图代码：如果脚本中使用了 playwright 且未手动截图，则自动截图
    """
    tmp_dir = tempfile.mkdtemp(prefix="qh_run_")
    script_path = Path(tmp_dir) / "test_script.py"
    screenshot_dir = Path(tmp_dir) / "screenshots"
    screenshot_dir.mkdir()
    try:
        # 如果脚本使用 playwright 且没有手动调用 screenshot，注入自动截图
        final_script = _inject_auto_screenshot(script, str(screenshot_dir))
        script_path.write_text(final_script, encoding="utf-8")
        # 通过环境变量告诉脚本截图保存位置
        env = {**os.environ, "QH_SCREENSHOT_DIR": str(screenshot_dir)}
        proc = await asyncio.create_subprocess_exec(
            sys.executable, str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tmp_dir,
            env=env,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        log = (stdout.decode() + "\n" + stderr.decode()).strip()
        status = "passed" if proc.returncode == 0 else "failed"
        # 收集截图文件，移动到持久化目录
        saved_screenshots = _collect_screenshots(screenshot_dir)
        return status, log, saved_screenshots
    except asyncio.TimeoutError:
        proc.kill()  # type: ignore
        saved_screenshots = _collect_screenshots(screenshot_dir)
        return "failed", f"执行超时（{timeout}s）", saved_screenshots
    except Exception as e:
        return "failed", f"执行异常: {e}", []
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _inject_auto_screenshot(script: str, screenshot_dir: str) -> str:
    """如果脚本使用 playwright 但没有手动截图，在 browser.close() 前注入自动截图"""
    if "playwright" not in script:
        return script
    if ".screenshot(" in script:
        # 已有手动截图，不注入
        return script
    # 注入：在脚本末尾添加自动截图逻辑（通过 wrapper 方式）
    wrapper = f'''
import os as _os
_screenshot_dir = "{screenshot_dir}"

# 自动截图：monkey-patch browser.close 在关闭前截图
import playwright.sync_api as _pw_module
_original_close = _pw_module.Browser.close
def _auto_close(self):
    try:
        for ctx in self.contexts:
            for pg in ctx.pages:
                pg.screenshot(path=_os.path.join(_screenshot_dir, "auto_final.png"))
                break
            break
    except Exception:
        pass
    _original_close(self)
_pw_module.Browser.close = _auto_close
'''
    return wrapper + "\n" + script


def _collect_screenshots(screenshot_dir: Path) -> list[str]:
    """收集截图目录中的图片文件，上传到 freeimage.host 图床，返回 URL 列表"""
    import base64
    import urllib.parse
    import urllib.request

    urls = []
    if not screenshot_dir.exists():
        return urls
    for f in sorted(screenshot_dir.iterdir()):
        if f.suffix.lower() in (".png", ".jpg", ".jpeg"):
            try:
                b64 = base64.b64encode(f.read_bytes()).decode()
                data = urllib.parse.urlencode({
                    "key": _IMAGE_HOSTING_KEY,
                    "source": b64,
                    "format": "json",
                }).encode()
                req = urllib.request.Request(_IMAGE_HOSTING_API, data=data, method="POST")
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read())
                if result.get("status_code") == 200:
                    urls.append(result["image"]["url"])
                    logger.info(f"截图上传成功: {f.name} -> {urls[-1]}")
                else:
                    logger.warning(f"截图上传失败: {f.name}, 响应: {result}")
            except Exception as e:
                logger.error(f"截图上传异常: {f.name}, {e}")
    return urls


async def _recalculate_run(db, run_id: str) -> None:
    """重新计算run的统计数据，检查是否全部完成"""
    cursor = await db.execute("SELECT status FROM run_results WHERE run_id = ?", (run_id,))
    rows = await cursor.fetchall()
    passed = sum(1 for r in rows if r["status"] == "passed")
    failed = sum(1 for r in rows if r["status"] == "failed")
    skipped = sum(1 for r in rows if r["status"] == "skipped")
    pending = sum(1 for r in rows if r["status"] == "pending")

    now = datetime.now(_SHANGHAI_TZ).isoformat()
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



