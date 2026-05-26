"""backend/app/routers/cases.py — 测试用例管理 API

端点: POST/GET /cases, GET/PUT/DELETE /cases/{id}
"""
from __future__ import annotations

import uuid
from fastapi import APIRouter, Query
from loguru import logger

from app.database import get_db
from app.models.schemas import CaseCreate, CaseUpdate, CaseOut
from app.utils.exceptions import NotFoundException, ConflictException

router = APIRouter(tags=["cases"])


def _row_to_case(r) -> CaseOut:
    return CaseOut(
        id=r["id"], featureId=r["feature_id"], title=r["title"],
        steps=r["steps"] or None, expectedResult=r["expected_result"] or None,
        priority=r["priority"], caseType=r["case_type"],
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
            (case_id, body.feature_id, body.title, body.steps,
             body.expected_result, body.priority.value, body.case_type.value, body.midscene_script),
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
                (case_id, item.feature_id, item.title, item.steps,
                 item.expected_result, item.priority.value, item.case_type.value, item.midscene_script),
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
            params.append(body.steps)
        if body.expected_result is not None:
            updates.append("expected_result = ?")
            params.append(body.expected_result)
        if body.priority is not None:
            updates.append("priority = ?")
            params.append(body.priority.value)
        if body.case_type is not None:
            updates.append("case_type = ?")
            params.append(body.case_type.value)
        if body.midscene_script is not None:
            updates.append("midscene_script = ?")
            params.append(body.midscene_script)

        if updates:
            updates.append("updated_at = datetime('now')")
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
    """删除测试用例"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM cases WHERE id = ?", (case_id,))
        if not await cursor.fetchone():
            raise NotFoundException(f"未找到 ID 为 {case_id} 的测试用例")

        await db.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        await db.commit()
        logger.info(f"删除测试用例: {case_id}")
        return {"ok": True}
    finally:
        await db.close()
