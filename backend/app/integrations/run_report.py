"""backend/app/integrations/run_report.py — run 结束后把结果写成需求评论

按功能点上的 pm_item_key 分组：同一个需求下的用例合成一条评论，
写通过 / 失败 / 跳过的条数、通过率（不含跳过）、失败用例标题和 run 链接。
没有关联需求的用例不写；项目管理客户端未启用时什么都不做。
"""
from __future__ import annotations

import os

import httpx
from loguru import logger

from app.database import get_db
from app.integrations.pm import PMClient, PMError

_MAX_FAILED_LISTED = 10


def _run_link(project_id: str, run_id: str) -> str:
    base = os.environ.get("QH_PUBLIC_URL", "").strip().rstrip("/")
    path = f"/projects/{project_id}/runs/{run_id}"
    return f"{base}{path}" if base else path


def build_comment(project_id: str, run_id: str, rows: list[dict]) -> str:
    """rows：同一个需求下的结果，每行含 status、case_title"""
    passed = sum(1 for r in rows if r["status"] == "passed")
    failed = [r for r in rows if r["status"] == "failed"]
    skipped = sum(1 for r in rows if r["status"] == "skipped")
    effective = passed + len(failed)
    rate = f"{passed / effective * 100:.1f}%" if effective else "无（全部跳过）"
    lines = [
        "【quality-hub 执行结果】",
        f"用例 {len(rows)} 条：通过 {passed}、失败 {len(failed)}、跳过 {skipped}；通过率 {rate}",
    ]
    if failed:
        lines.append("失败用例：")
        lines += [f"- {r['case_title'] or '（无标题）'}" for r in failed[:_MAX_FAILED_LISTED]]
        if len(failed) > _MAX_FAILED_LISTED:
            lines.append(f"- 另有 {len(failed) - _MAX_FAILED_LISTED} 条，见执行详情")
    lines.append(f"执行详情：{_run_link(project_id, run_id)}")
    return "\n".join(lines)


async def report_run(run_id: str, transport: httpx.AsyncBaseTransport | None = None) -> dict[str, str]:
    """把一次 run 的结果写到关联需求下。返回 {需求编号: "ok" 或错误说明}；客户端未启用返回 {}"""
    client = PMClient.from_env(transport)
    if client is None:
        return {}
    db = await get_db()
    try:
        cursor = await db.execute("SELECT project_id FROM runs WHERE id = ?", (run_id,))
        run = await cursor.fetchone()
        if not run:
            return {}
        cursor = await db.execute(
            """SELECT rr.status, c.title AS case_title, f.pm_item_key
               FROM run_results rr
               JOIN cases c ON rr.case_id = c.id
               JOIN features f ON c.feature_id = f.id
               WHERE rr.run_id = ? AND f.pm_item_key IS NOT NULL
               ORDER BY f.pm_item_key, c.title""",
            (run_id,),
        )
        groups: dict[str, list[dict]] = {}
        for r in await cursor.fetchall():
            groups.setdefault(r["pm_item_key"], []).append(dict(r))
    finally:
        await db.close()

    outcome: dict[str, str] = {}
    for key, rows in groups.items():
        try:
            await client.add_comment(key, build_comment(run["project_id"], run_id, rows))
            outcome[key] = "ok"
        except (PMError, httpx.HTTPError) as e:
            logger.warning(f"写项目管理评论失败 run={run_id} item={key}: {e}")
            outcome[key] = str(e)
    return outcome
