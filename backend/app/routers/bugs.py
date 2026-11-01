"""backend/app/routers/bugs.py — 失败用例转缺陷（测试人员确认后才建）

端点:
- GET  /runs/{run_id}/results/{result_id}/bug-draft  生成缺陷草稿，只预览，不建
- POST /runs/{run_id}/results/{result_id}/bug        测试人员确认（可改标题、严重程度、描述）后在项目管理建缺陷
"""
from __future__ import annotations

import json
import os

import httpx
from fastapi import APIRouter
from loguru import logger

from app.database import get_db
from app.integrations.pm import PMError, pm_error_to_app, require_client
from app.models.schemas import BugDraft
from app.utils.exceptions import ConflictException, ForbiddenException, NotFoundException

router = APIRouter(tags=["bugs"])

# 用例优先级 → 缺陷严重程度；critical 只由人定
SEVERITY_BY_PRIORITY = {"high": "major", "medium": "normal", "low": "minor"}
_LOG_TAIL = 1500


async def _load(run_id: str, result_id: str):
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT rr.*, c.title AS case_title, c.priority, c.steps, c.expected_result,
                      f.title AS feature_title, f.pm_item_key, p.pm_project_key, p.id AS project_id
               FROM run_results rr
               JOIN cases c ON rr.case_id = c.id
               JOIN features f ON c.feature_id = f.id
               JOIN runs r ON rr.run_id = r.id
               JOIN projects p ON r.project_id = p.id
               WHERE rr.id = ? AND rr.run_id = ?""",
            (result_id, run_id),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()
    if not row:
        raise NotFoundException("执行结果不存在")
    if row["status"] != "failed":
        raise ForbiddenException("只有失败的结果才能提缺陷")
    if row["pm_bug_key"]:
        raise ConflictException(f"这条结果已经提过缺陷 {row['pm_bug_key']}")
    if not row["pm_project_key"]:
        raise ForbiddenException("项目没有关联项目管理，不能提缺陷")
    return row


def _draft(row) -> BugDraft:
    base = os.environ.get("QH_PUBLIC_URL", "").strip().rstrip("/")
    link = f"{base}/projects/{row['project_id']}/runs/{row['run_id']}"
    shots = json.loads(row["screenshots"] or "[]")
    lines = [
        f"quality-hub 用例执行失败：{row['case_title']}",
        f"功能点：{row['feature_title']}" + (f"（需求 {row['pm_item_key']}）" if row["pm_item_key"] else ""),
        f"预期结果：{row['expected_result'] or '无'}",
        "错误信息：",
        (row["error_message"] or "无")[-_LOG_TAIL:],
    ]
    if shots:
        lines.append("截图：")
        lines += [f"- {s}" for s in shots]
    lines.append(f"执行详情：{link}")
    return BugDraft(
        title=f"[用例失败] {row['case_title']}"[:200],
        description="\n".join(lines),
        severity=SEVERITY_BY_PRIORITY.get(row["priority"], "normal"),
    )


@router.get("/runs/{run_id}/results/{result_id}/bug-draft", response_model=BugDraft)
async def bug_draft(run_id: str, result_id: str):
    """生成缺陷草稿给测试人员确认，不建缺陷"""
    return _draft(await _load(run_id, result_id))


@router.post("/runs/{run_id}/results/{result_id}/bug")
async def create_bug(run_id: str, result_id: str, body: BugDraft):
    """测试人员确认后建缺陷，缺陷编号写回这条结果"""
    row = await _load(run_id, result_id)
    client = require_client()
    try:
        item = await client.create_bug(row["pm_project_key"], body.title, body.description, body.severity)
    except (PMError, httpx.HTTPError) as e:
        raise pm_error_to_app(e)
    db = await get_db()
    try:
        await db.execute("UPDATE run_results SET pm_bug_key = ? WHERE id = ?", (item["key"], result_id))
        await db.commit()
    finally:
        await db.close()
    logger.info(f"失败用例已转缺陷: result={result_id} bug={item['key']}")
    return {"pmBugKey": item["key"]}
