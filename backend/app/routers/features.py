"""backend/app/routers/features.py — 功能点管理 API"""
from __future__ import annotations

import uuid
from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from app.database import get_db
from app.models.schemas import FeatureCreate, FeatureOut

router = APIRouter(tags=["features"])


@router.post("/features", response_model=FeatureOut)
async def create_feature(body: FeatureCreate):
    """创建功能点"""
    db = await get_db()
    try:
        # 校验项目存在
        cursor = await db.execute("SELECT id FROM projects WHERE id = ?", (body.project_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="项目不存在")

        feature_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO features (id, project_id, name, description) VALUES (?, ?, ?, ?)",
            (feature_id, body.project_id, body.name, body.description),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM features WHERE id = ?", (feature_id,))
        row = await cursor.fetchone()
        logger.info(f"创建功能点: {body.name} (project={body.project_id})")
        return FeatureOut(
            id=row["id"], projectId=row["project_id"], name=row["name"],
            description=row["description"], status=row["status"], createdAt=row["created_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建功能点失败: {e}")
        raise HTTPException(status_code=500, detail="创建功能点失败")
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
        return [
            FeatureOut(
                id=r["id"], projectId=r["project_id"], name=r["name"],
                description=r["description"], status=r["status"], createdAt=r["created_at"],
            )
            for r in rows
        ]
    except Exception as e:
        logger.error(f"获取功能点列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取功能点列表失败")
    finally:
        await db.close()
