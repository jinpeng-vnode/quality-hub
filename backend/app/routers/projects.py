"""backend/app/routers/projects.py — 项目管理 API"""
from __future__ import annotations

import uuid
from fastapi import APIRouter, HTTPException
from loguru import logger

from app.database import get_db
from app.models.schemas import ProjectCreate, ProjectOut

router = APIRouter(tags=["projects"])


@router.post("/projects", response_model=ProjectOut)
async def create_project(body: ProjectCreate):
    """创建项目"""
    db = await get_db()
    try:
        project_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO projects (id, name, description) VALUES (?, ?, ?)",
            (project_id, body.name, body.description),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = await cursor.fetchone()
        logger.info(f"创建项目: {body.name} (id={project_id})")
        return ProjectOut(id=row["id"], name=row["name"], description=row["description"], createdAt=row["created_at"])
    except Exception as e:
        logger.error(f"创建项目失败: {e}")
        raise HTTPException(status_code=500, detail="创建项目失败")
    finally:
        await db.close()


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects():
    """获取项目列表"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM projects ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [
            ProjectOut(id=r["id"], name=r["name"], description=r["description"], createdAt=r["created_at"])
            for r in rows
        ]
    except Exception as e:
        logger.error(f"获取项目列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取项目列表失败")
    finally:
        await db.close()
