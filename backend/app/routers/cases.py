"""backend/app/routers/cases.py — 测试用例管理 API"""
from __future__ import annotations

import json
import uuid
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.database import get_db
from app.models.schemas import CaseCreate, CaseUpdate, CaseOut

router = APIRouter(tags=["cases"])


def _row_to_case(r) -> CaseOut:
    steps = json.loads(r["steps"]) if isinstance(r["steps"], str) else r["steps"]
    return CaseOut(
        id=r["id"], featureId=r["feature_id"], title=r["title"],
        steps=steps, expected=r["expected"], priority=r["priority"],
        status=r["status"], createdAt=r["created_at"], updatedAt=r["updated_at"],
    )


@router.post("/cases", response_model=CaseOut)
async def create_case(body: CaseCreate):
    """创建测试用例"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM features WHERE id = ?", (body.feature_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="功能点不存在")

        case_id = str(uuid.uuid4())
        steps_json = json.dumps(body.steps, ensure_ascii=False)
        await db.execute(
            "INSERT INTO cases (id, feature_id, title, steps, expected, priority) VALUES (?, ?, ?, ?, ?, ?)",
            (case_id, body.feature_id, body.title, steps_json, body.expected, body.priority),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        row = await cursor.fetchone()
        logger.info(f"创建测试用例: {body.title}")
        return _row_to_case(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建测试用例失败: {e}")
        raise HTTPException(status_code=500, detail="创建测试用例失败")
    finally:
        await db.close()


@router.get("/cases", response_model=list[CaseOut])
async def list_cases(feature_id: str = Query(..., alias="featureId")):
    """获取测试用例列表（按功能点筛选）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM cases WHERE feature_id = ? ORDER BY created_at DESC",
            (feature_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_case(r) for r in rows]
    except Exception as e:
        logger.error(f"获取测试用例列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取测试用例列表失败")
    finally:
        await db.close()


@router.put("/cases/{case_id}", response_model=CaseOut)
async def update_case(case_id: str, body: CaseUpdate):
    """更新测试用例"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        existing = await cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="测试用例不存在")

        updates = []
        params = []
        if body.title is not None:
            updates.append("title = ?")
            params.append(body.title)
        if body.steps is not None:
            updates.append("steps = ?")
            params.append(json.dumps(body.steps, ensure_ascii=False))
        if body.expected is not None:
            updates.append("expected = ?")
            params.append(body.expected)
        if body.priority is not None:
            updates.append("priority = ?")
            params.append(body.priority)
        if body.status is not None:
            updates.append("status = ?")
            params.append(body.status)

        if updates:
            updates.append("updated_at = datetime('now')")
            sql = f"UPDATE cases SET {', '.join(updates)} WHERE id = ?"
            params.append(case_id)
            await db.execute(sql, params)
            await db.commit()

        cursor = await db.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        row = await cursor.fetchone()
        logger.info(f"更新测试用例: {case_id}")
        return _row_to_case(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新测试用例失败: {e}")
        raise HTTPException(status_code=500, detail="更新测试用例失败")
    finally:
        await db.close()


@router.delete("/cases/{case_id}")
async def delete_case(case_id: str):
    """删除测试用例"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM cases WHERE id = ?", (case_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="测试用例不存在")

        await db.execute("DELETE FROM cases WHERE id = ?", (case_id,))
        await db.commit()
        logger.info(f"删除测试用例: {case_id}")
        return {"message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除测试用例失败: {e}")
        raise HTTPException(status_code=500, detail="删除测试用例失败")
    finally:
        await db.close()
