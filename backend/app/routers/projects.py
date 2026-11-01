"""backend/app/routers/projects.py — 项目管理 API

端点: POST/GET /projects, GET/PUT/DELETE /projects/{id}
"""
from __future__ import annotations

import uuid

import httpx
from fastapi import APIRouter
from loguru import logger

from app.database import get_db
from app.integrations.pm import PMError, pm_error_to_app, require_client
from app.models.schemas import ProjectImport, ProjectUpdate, ProjectOut
from app.utils.exceptions import NotFoundException, ConflictException

router = APIRouter(tags=["projects"])


def _row_to_project(r) -> ProjectOut:
    return ProjectOut(
        id=r["id"], name=r["name"], repoUrl=r["repo_url"] or None,
        description=r["description"] or None, pmProjectKey=r["pm_project_key"],
        createdAt=r["created_at"], updatedAt=r["updated_at"],
    )


@router.post("/projects/import", response_model=ProjectOut)
async def import_project(body: ProjectImport):
    """从项目管理导入项目（项目只能这样建）：名称、描述取项目管理里的"""
    client = require_client()
    try:
        pm_project = await client.get_project(body.pm_project_key)
    except (PMError, httpx.HTTPError) as e:
        raise pm_error_to_app(e)

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM projects WHERE pm_project_key = ?", (body.pm_project_key,),
        )
        if await cursor.fetchone():
            raise ConflictException(f"项目 {body.pm_project_key} 已导入")

        project_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO projects (id, name, repo_url, description, pm_project_key) VALUES (?, ?, ?, ?, ?)",
            (project_id, pm_project["name"], body.repo_url or "", pm_project.get("description") or "",
             body.pm_project_key),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = await cursor.fetchone()
        logger.info(f"从项目管理导入项目: {body.pm_project_key} (id={project_id})")
        return _row_to_project(row)
    finally:
        await db.close()


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects():
    """获取项目列表"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM projects ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [_row_to_project(r) for r in rows]
    finally:
        await db.close()


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str):
    """获取项目详情"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = await cursor.fetchone()
        if not row:
            raise NotFoundException(f"未找到 ID 为 {project_id} 的项目")
        return _row_to_project(row)
    finally:
        await db.close()


@router.put("/projects/{project_id}", response_model=ProjectOut)
async def update_project(project_id: str, body: ProjectUpdate):
    """更新项目"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not await cursor.fetchone():
            raise NotFoundException(f"未找到 ID 为 {project_id} 的项目")

        updates, params = [], []
        if body.repo_url is not None:
            updates.append("repo_url = ?")
            params.append(body.repo_url)

        if updates:
            updates.append("updated_at = datetime('now', '+8 hours')")
            params.append(project_id)
            await db.execute(f"UPDATE projects SET {', '.join(updates)} WHERE id = ?", params)
            await db.commit()

        cursor = await db.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = await cursor.fetchone()
        logger.info(f"更新项目: {project_id}")
        return _row_to_project(row)
    finally:
        await db.close()


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """删除项目（级联删除所有关联数据）"""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not await cursor.fetchone():
            raise NotFoundException(f"未找到 ID 为 {project_id} 的项目")

        # 级联删除：run_results → runs → cases → features → project
        await db.execute(
            "DELETE FROM run_results WHERE run_id IN (SELECT id FROM runs WHERE project_id = ?)",
            (project_id,),
        )
        await db.execute("DELETE FROM runs WHERE project_id = ?", (project_id,))
        await db.execute(
            "DELETE FROM run_results WHERE case_id IN (SELECT c.id FROM cases c JOIN features f ON c.feature_id = f.id WHERE f.project_id = ?)",
            (project_id,),
        )
        await db.execute(
            "DELETE FROM cases WHERE feature_id IN (SELECT id FROM features WHERE project_id = ?)",
            (project_id,),
        )
        await db.execute("DELETE FROM features WHERE project_id = ?", (project_id,))
        await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        await db.commit()
        logger.info(f"删除项目: {project_id}")
        return {"ok": True}
    finally:
        await db.close()
