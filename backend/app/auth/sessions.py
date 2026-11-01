"""backend/app/auth/sessions.py — quality-hub 自己的会话

会话串只放在 Cookie 里，库里只存它的 SHA-256 哈希；会话串原文不进日志。
"""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from app.database import get_db

COOKIE_NAME = "qh_session"


def session_hours() -> int:
    try:
        return max(1, int(os.environ.get("QH_SESSION_HOURS", "12")))
    except ValueError:
        return 12


def cookie_secure() -> bool:
    """线上走 https 时设 QH_COOKIE_SECURE=1；默认关（内网 http）"""
    return os.environ.get("QH_COOKIE_SECURE", "").strip() == "1"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create(user_id: int, username: str, display_name: str) -> str:
    token = secrets.token_urlsafe(32)
    expires = (_now() + timedelta(hours=session_hours())).isoformat()
    db = await get_db()
    try:
        await db.execute("DELETE FROM sessions WHERE expires_at < ?", (_now().isoformat(),))
        await db.execute(
            "INSERT INTO sessions (token_hash, user_id, username, display_name, expires_at) VALUES (?, ?, ?, ?, ?)",
            (_hash(token), user_id, username, display_name, expires),
        )
        await db.commit()
    finally:
        await db.close()
    return token


async def lookup(token: str | None) -> dict | None:
    """有效会话返回 {id, username, display_name}，否则 None"""
    if not token:
        return None
    db = await get_db()
    try:
        cur = await db.execute(
            "SELECT user_id, username, display_name, expires_at FROM sessions WHERE token_hash = ?",
            (_hash(token),),
        )
        row = await cur.fetchone()
    finally:
        await db.close()
    if not row or row["expires_at"] < _now().isoformat():
        return None
    return {"id": row["user_id"], "username": row["username"], "display_name": row["display_name"]}


async def delete(token: str | None) -> None:
    if not token:
        return
    db = await get_db()
    try:
        await db.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash(token),))
        await db.commit()
    finally:
        await db.close()
