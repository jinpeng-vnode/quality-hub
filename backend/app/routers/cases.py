"""backend/app/routers/cases.py — 测试用例管理 API

端点: POST/GET /cases, GET/PUT/DELETE /cases/{id}
"""
from __future__ import annotations

import json
import uuid
from fastapi import APIRouter, Query
from loguru import logger

from app.database import get_db
from app.models.schemas import CaseCreate, CaseUpdate, CaseOut
from app.utils.exceptions import NotFoundException, ConflictException

router = APIRouter(tags=["cases"])


def _row_to_case(r) -> CaseOut:
    # steps 存储为 JSON 数组字符串，解析为 list
    steps_raw = r["steps"] or "[]"
    try:
        steps = json.loads(steps_raw) if steps_raw else []
        if not isinstance(steps, list):
            steps = [steps_raw] if steps_raw else []
    except (json.JSONDecodeError, TypeError):
        steps = [steps_raw] if steps_raw else []
    return CaseOut(
        id=r["id"], featureId=r["feature_id"], title=r["title"],
        steps=steps, expectedResult=r["expected_result"] or None,
        priority=r["priority"],
        midsceneScript=r["midscene_script"],
        createdAt=r["created_at"], updatedAt=r["updated_at"],
    )


@router.post("/cases", response_model=CaseOut)
async def create_case(body: CaseCreate):
    """创建测试用例"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM features WHERE id = ?", (body.feature_id,))
        if not await cursor.fetchone():
            raise NotFoundException("功能点不存在")

        # TC-033: 功能点内用例标题唯一性检查
        cursor = await db.execute(
            "SELECT id FROM cases WHERE feature_id = ? AND title = ?",
            (body.feature_id, body.title),
        )
        if await cursor.fetchone():
            raise ConflictException("该功能点下用例标题已存在")

        case_id = str(uuid.uuid4())
        await db.execute(
            """INSERT INTO cases (id, feature_id, title, steps, expected_result, priority, case_type, midscene_script)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (case_id, body.feature_id, body.title, json.dumps(body.steps),
             body.expected_result, body.priority.value, "e2e", body.midscene_script),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        row = await cursor.fetchone()
        logger.info(f"创建测试用例: {body.title}")
        return _row_to_case(row)
    finally:
        await db.close()


@router.post("/cases/batch", response_model=list[CaseOut])
async def create_cases_batch(body: list[CaseCreate]):
    """TC-034/035: 批量创建测试用例"""
    db = await get_db()
    try:
        results = []
        for item in body:
            cursor = await db.execute("SELECT id FROM features WHERE id = ?", (item.feature_id,))
            if not await cursor.fetchone():
                raise NotFoundException(f"功能点不存在: {item.feature_id}")
            cursor = await db.execute(
                "SELECT id FROM cases WHERE feature_id = ? AND title = ?",
                (item.feature_id, item.title),
            )
            if await cursor.fetchone():
                raise ConflictException(f"该功能点下用例标题已存在: {item.title}")

            case_id = str(uuid.uuid4())
            await db.execute(
                """INSERT INTO cases (id, feature_id, title, steps, expected_result, priority, case_type, midscene_script)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (case_id, item.feature_id, item.title, json.dumps(item.steps),
                 item.expected_result, item.priority.value, "e2e", item.midscene_script),
            )
            cursor = await db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
            results.append(_row_to_case(await cursor.fetchone()))
        await db.commit()
        logger.info(f"批量创建测试用例: {len(results)} 条")
        return results
    finally:
        await db.close()


@router.get("/cases", response_model=list[CaseOut])
async def list_cases(
    feature_id: str | None = Query(None, alias="featureId"),
    project_id: str | None = Query(None, alias="projectId"),
):
    """获取测试用例列表（按功能点或项目筛选）"""
    db = await get_db()
    try:
        if feature_id:
            cursor = await db.execute(
                "SELECT * FROM cases WHERE feature_id = ? ORDER BY created_at DESC",
                (feature_id,),
            )
        elif project_id:
            cursor = await db.execute(
                "SELECT c.* FROM cases c JOIN features f ON c.feature_id = f.id WHERE f.project_id = ? ORDER BY c.created_at DESC",
                (project_id,),
            )
        else:
            return []
        return [_row_to_case(r) for r in await cursor.fetchall()]
    finally:
        await db.close()


@router.get("/cases/{case_id}", response_model=CaseOut)
async def get_case(case_id: str):
    """获取用例详情"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        row = await cursor.fetchone()
        if not row:
            raise NotFoundException(f"未找到 ID 为 {case_id} 的测试用例")
        return _row_to_case(row)
    finally:
        await db.close()


@router.put("/cases/{case_id}", response_model=CaseOut)
async def update_case(case_id: str, body: CaseUpdate):
    """更新测试用例"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM cases WHERE id = ?", (case_id,))
        if not await cursor.fetchone():
            raise NotFoundException(f"未找到 ID 为 {case_id} 的测试用例")

        updates, params = [], []
        if body.title is not None:
            updates.append("title = ?")
            params.append(body.title)
        if body.steps is not None:
            updates.append("steps = ?")
            params.append(json.dumps(body.steps))
        if body.expected_result is not None:
            updates.append("expected_result = ?")
            params.append(body.expected_result)
        if body.priority is not None:
            updates.append("priority = ?")
            params.append(body.priority.value)
        if body.midscene_script is not None:
            updates.append("midscene_script = ?")
            params.append(body.midscene_script)

        if updates:
            updates.append("updated_at = datetime('now', '+8 hours')")
            params.append(case_id)
            await db.execute(f"UPDATE cases SET {', '.join(updates)} WHERE id = ?", params)
            await db.commit()

        cursor = await db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        row = await cursor.fetchone()
        logger.info(f"更新测试用例: {case_id}")
        return _row_to_case(row)
    finally:
        await db.close()


@router.delete("/cases/{case_id}")
async def delete_case(case_id: str):
    """删除测试用例（级联删除关联的 run_results）"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM cases WHERE id = ?", (case_id,))
        if not await cursor.fetchone():
            raise NotFoundException(f"未找到 ID 为 {case_id} 的测试用例")

        # 级联删除关联的执行结果
        await db.execute("DELETE FROM run_results WHERE case_id = ?", (case_id,))
        await db.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        await db.commit()
        logger.info(f"删除测试用例: {case_id}")
        return {"ok": True}
    finally:
        await db.close()


@router.post("/cases/{case_id}/execute")
async def execute_case(case_id: str):
    """即时执行单条用例脚本，同步返回结果（用于编辑时验证脚本）"""
    from app.routers.runs import _run_single_script

    db = await get_db()
    try:
        cursor = await db.execute("SELECT midscene_script FROM cases WHERE id = ?", (case_id,))
        row = await cursor.fetchone()
        if not row:
            raise NotFoundException("用例不存在")
        script = row["midscene_script"] or ""
        if not script:
            return {"status": "skipped", "log": "无脚本", "durationMs": 0, "screenshots": []}
    finally:
        await db.close()

    import time
    start = time.time()
    status, log, screenshots = await _run_single_script(script, timeout=60)
    duration_ms = int((time.time() - start) * 1000)
    return {"status": status, "log": log, "durationMs": duration_ms, "screenshots": screenshots}
