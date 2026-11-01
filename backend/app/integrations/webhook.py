"""backend/app/integrations/webhook.py — 接收项目管理的 webhook

POST /api/integrations/pm/webhook
- 只认 X-PM-Signature（sha256=<hex HMAC-SHA256(PM_WEBHOOK_SECRET, body)>），没配密钥或签名不对一律 401。
- item.transitioned：缺陷进入「测试」→ 关联这条缺陷的结果标「待回归」。
- deployment.created：按项目跑一次冒烟用例；同一个部署编号只跑一次。
其余事件回 200 不处理。
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os

from fastapi import APIRouter, Request
from loguru import logger

from app.database import get_db
from app.utils.exceptions import AppException

router = APIRouter(tags=["integrations"])
_smoke_lock = asyncio.Lock()


def verify_signature(secret: str, body: bytes, header: str | None) -> bool:
    if not secret or not header:
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)


async def _mark_regression(bug_key: str) -> int:
    db = await get_db()
    try:
        cur = await db.execute("UPDATE run_results SET regression_pending = 1 WHERE pm_bug_key = ?", (bug_key,))
        await db.commit()
        return cur.rowcount
    finally:
        await db.close()


async def _run_smoke(pm_project_key: str, deploy_no: str) -> str | None:
    """返回新建的 run id；没有对应项目、没有冒烟用例或这个部署已经跑过就返回 None"""
    from app.models.schemas import RunCreate
    from app.routers.runs import create_run

    trigger = f"deploy:{deploy_no}"
    async with _smoke_lock:
        db = await get_db()
        try:
            cur = await db.execute("SELECT id FROM projects WHERE pm_project_key = ?", (pm_project_key,))
            project = await cur.fetchone()
            if not project:
                return None
            cur = await db.execute(
                "SELECT id FROM runs WHERE project_id = ? AND trigger_ref = ?", (project["id"], trigger),
            )
            if await cur.fetchone():
                return None
            cur = await db.execute(
                """SELECT c.id FROM cases c JOIN features f ON c.feature_id = f.id
                   WHERE f.project_id = ? AND c.is_smoke = 1""",
                (project["id"],),
            )
            case_ids = [r["id"] for r in await cur.fetchall()]
        finally:
            await db.close()
        if not case_ids:
            return None
        run = await create_run(RunCreate(projectId=project["id"], caseIds=case_ids))
        db = await get_db()
        try:
            await db.execute("UPDATE runs SET trigger_ref = ? WHERE id = ?", (trigger, run.id))
            await db.commit()
        finally:
            await db.close()
        return run.id


@router.post("/integrations/pm/webhook")
async def pm_webhook(request: Request):
    body = await request.body()
    secret = os.environ.get("PM_WEBHOOK_SECRET", "").strip()
    if not verify_signature(secret, body, request.headers.get("x-pm-signature")):
        raise AppException("UNAUTHORIZED", "webhook 签名校验失败", status_code=401)
    try:
        ev = json.loads(body)
    except ValueError:
        raise AppException("BAD_REQUEST", "webhook 内容不是 JSON", status_code=400)

    name = ev.get("event")
    item = ev.get("item") or {}
    if name == "item.transitioned" and item.get("kind") == "bug" and (ev.get("transition") or {}).get("to") == "testing":
        n = await _mark_regression(item["key"])
        logger.info(f"缺陷进入测试，标待回归: {item['key']}（{n} 条结果）")
        return {"ok": True, "handled": "regression", "marked": n}
    if name == "deployment.created":
        deploy_no = str((ev.get("data") or {}).get("deploy_no") or "")
        project_key = (ev.get("project") or {}).get("key", "")
        if deploy_no and project_key:
            run_id = await _run_smoke(project_key, deploy_no)
            logger.info(f"部署 {deploy_no}（{project_key}）冒烟: run={run_id}")
            return {"ok": True, "handled": "smoke", "runId": run_id}
    return {"ok": True, "handled": None}
