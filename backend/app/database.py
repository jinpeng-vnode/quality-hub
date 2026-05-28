"""backend/app/database.py — SQLite 数据库连接与初始化"""
from __future__ import annotations

import aiosqlite
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "quality_hub.db"


async def get_db() -> aiosqlite.Connection:
    """获取数据库连接"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db() -> None:
    """初始化数据库表结构"""
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                repo_url TEXT DEFAULT '',
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now', '+8 hours')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', '+8 hours'))
            );

            CREATE TABLE IF NOT EXISTS features (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                source TEXT DEFAULT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL DEFAULT (datetime('now', '+8 hours')),
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS cases (
                id TEXT PRIMARY KEY,
                feature_id TEXT NOT NULL,
                title TEXT NOT NULL,
                steps TEXT DEFAULT '',
                expected_result TEXT DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'medium',
                case_type TEXT NOT NULL DEFAULT 'manual',
                midscene_script TEXT DEFAULT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', '+8 hours')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', '+8 hours')),
                FOREIGN KEY (feature_id) REFERENCES features(id)
            );

            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                mode TEXT NOT NULL DEFAULT 'manual',
                total INTEGER NOT NULL DEFAULT 0,
                passed INTEGER NOT NULL DEFAULT 0,
                failed INTEGER NOT NULL DEFAULT 0,
                skipped INTEGER NOT NULL DEFAULT 0,
                started_at TEXT,
                finished_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now', '+8 hours')),
                FOREIGN KEY (project_id) REFERENCES projects(id)
            );

            CREATE TABLE IF NOT EXISTS run_results (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                case_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                error_message TEXT DEFAULT '',
                duration_ms INTEGER DEFAULT 0,
                log TEXT DEFAULT '',
                FOREIGN KEY (run_id) REFERENCES runs(id),
                FOREIGN KEY (case_id) REFERENCES cases(id)
            );
        """)
        await db.commit()

        # 迁移：为已有数据库添加新字段（SQLite ALTER TABLE 不报错如果列已存在则忽略）
        migrations = [
            "ALTER TABLE runs ADD COLUMN mode TEXT NOT NULL DEFAULT 'manual'",
            "ALTER TABLE runs ADD COLUMN skipped INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE run_results ADD COLUMN log TEXT DEFAULT ''",
            "ALTER TABLE run_results ADD COLUMN screenshots TEXT DEFAULT '[]'",
        ]
        for sql in migrations:
            try:
                await db.execute(sql)
            except Exception:
                pass  # 列已存在，忽略
        await db.commit()

        # 数据迁移：将旧的 steps 纯文本转为 JSON 数组格式
        import json
        cursor = await db.execute("SELECT id, steps FROM cases WHERE steps IS NOT NULL AND steps != '' AND steps NOT LIKE '[%'")
        rows = await cursor.fetchall()
        for row in rows:
            old_steps = row["steps"]
            try:
                # 尝试解析，如果已经是 JSON 数组则跳过
                json.loads(old_steps)
            except (json.JSONDecodeError, TypeError):
                # 纯文本，转为单元素数组
                new_steps = json.dumps([old_steps])
                await db.execute("UPDATE cases SET steps = ? WHERE id = ?", (new_steps, row["id"]))
        await db.commit()
    finally:
        await db.close()
