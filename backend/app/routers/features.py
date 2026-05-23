"""backend/app/routers/features.py — 功能点管理 API

端点: POST/GET /features, GET/PUT/DELETE /features/{id}
"""
from __future__ import annotations

import uuid
from fastapi import APIRouter, Query
from loguru import logger

from app.database import get_db
from app.models.schemas import FeatureCreate, FeatureUpdate, FeatureOut
from app.utils.exceptions import NotFoundException, ConflictException

router = APIRouter(tags=["features"])


async def _row_to_feature(db, r) -> FeatureOut:
    """转换行数据为响应模型，包含 case_count"""
    cursor = await db.execute("SELECT COUNT(*) as c FROM cases WHERE feature_id = ?", (r["id"],))
    count_row = await cursor.fetchone()
    return FeatureOut(
        id=r["id"], projectId=r["project_id"], title=r["title"],
        description=r["description"] or None, source=r["source"],
        status=r["status"], caseCount=count_row["c"], createdAt=r["created_at"],
    )


@router.post("/features", response_model=FeatureOut)
async def create_feature(body: FeatureCreate):
    """创建功能点"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM projects WHERE id = ?", (body.project_id,))
        if not await cursor.fetchone():
            raise NotFoundException("项目不存在")

        # TC-022: 项目内功能点名称唯一性检查
        cursor = await db.execute(
            "SELECT id FROM features WHERE project_id = ? AND title = ?",
            (body.project_id, body.title),
        )
        if await cursor.fetchone():
            raise ConflictException("该项目下功能点名称已存在")

        feature_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO features (id, project_id, title, description, source) VALUES (?, ?, ?, ?, ?)",
            (feature_id, body.project_id, body.title, body.description or "", body.source),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM features WHERE id = ?", (feature_id,))
        row = await cursor.fetchone()
        logger.info(f"创建功能点: {body.title} (project={body.project_id})")
        return await _row_to_feature(db, row)
    finally:
        await db.close()


@router.get("/features", response_model=list[FeatureOut])
async def list_features(project_id: str = Query(..., alias="projectId")):
    """获取功能点列表（按项目筛选）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM features WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        )
        rows = await cursor.fetchall()
        return [await _row_to_feature(db, r) for r in rows]
    finally:
        await db.close()


@router.get("/features/{feature_id}", response_model=FeatureOut)
async def get_feature(feature_id: str):
    """获取功能点详情"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM features WHERE id = ?", (feature_id,))
        row = await cursor.fetchone()
        if not row:
            raise NotFoundException(f"未找到 ID 为 {feature_id} 的功能点")
        return await _row_to_feature(db, row)
    finally:
        await db.close()


@router.put("/features/{feature_id}", response_model=FeatureOut)
async def update_feature(feature_id: str, body: FeatureUpdate):
    """更新功能点"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM features WHERE id = ?", (feature_id,))
        if not await cursor.fetchone():
            raise NotFoundException(f"未找到 ID 为 {feature_id} 的功能点")

        updates, params = [], []
        if body.title is not None:
            updates.append("title = ?")
            params.append(body.title)
        if body.description is not None:
            updates.append("description = ?")
            params.append(body.description)
        if body.status is not None:
            updates.append("status = ?")
            params.append(body.status.value)

        if updates:
            params.append(feature_id)
            await db.execute(f"UPDATE features SET {', '.join(updates)} WHERE id = ?", params)
            await db.commit()

        cursor = await db.execute("SELECT * FROM features WHERE id = ?", (feature_id,))
        row = await cursor.fetchone()
        logger.info(f"更新功能点: {feature_id}")
        return await _row_to_feature(db, row)
    finally:
        await db.close()


@router.delete("/features/{feature_id}")
async def delete_feature(feature_id: str):
    """删除功能点"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM features WHERE id = ?", (feature_id,))
        if not await cursor.fetchone():
            raise NotFoundException(f"未找到 ID 为 {feature_id} 的功能点")

        await db.execute("DELETE FROM features WHERE id = ?", (feature_id,))
        await db.commit()
        logger.info(f"删除功能点: {feature_id}")
        return {"ok": True}
    finally:
        await db.close()
