"""backend/app/auth/routes.py — 登录、退出、当前用户

账号和密码转给项目管理 POST /api/auth/login 校验，quality-hub 不存账号和密码。
校验通过后立即注销项目管理那边的会话，再由 quality-hub 自己发会话。
账号、密码、会话串都不进日志和报错信息。
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque

import httpx
from fastapi import APIRouter, Request, Response
from loguru import logger
from pydantic import BaseModel, Field

from app.auth import sessions
from app.integrations import pm as pm_mod
from app.utils.exceptions import AppException

router = APIRouter(tags=["auth"])

# 限流：同一个账号或同一个来源 IP，5 分钟内失败 5 次就先拒绝，直到窗口过去
_FAIL_WINDOW_S = 300
_FAIL_LIMIT = 5
_failures: dict[str, deque] = defaultdict(deque)


def _limited(keys: list[str]) -> bool:
    now = time.monotonic()
    for k in keys:
        q = _failures[k]
        while q and now - q[0] > _FAIL_WINDOW_S:
            q.popleft()
        if len(q) >= _FAIL_LIMIT:
            return True
    return False


def _record_failure(keys: list[str]) -> None:
    now = time.monotonic()
    for k in keys:
        _failures[k].append(now)


def reset_rate_limit() -> None:
    """测试用"""
    _failures.clear()


class LoginBody(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)


async def _pm_login(username: str, password: str) -> dict:
    base = os.environ.get("PM_BASE", "").strip().rstrip("/")
    if not base:
        raise AppException("PM_DISABLED", "未配置项目管理，无法登录", status_code=503)
    headers = {"X-Requested-With": "pm"}
    try:
        async with httpx.AsyncClient(base_url=base, transport=pm_mod._transport_override, timeout=15) as c:
            resp = await c.post("/api/auth/login", json={"username": username, "password": password}, headers=headers)
            if resp.status_code == 200:
                pm_session = resp.cookies.get("pm_session")
                try:
                    out = await c.post("/api/auth/logout", headers={**headers, "Cookie": f"pm_session={pm_session}"})
                    if out.status_code != 200:
                        logger.warning(f"注销项目管理会话失败: HTTP {out.status_code}")
                except httpx.HTTPError as e:
                    logger.warning(f"注销项目管理会话失败: {type(e).__name__}")
                return resp.json()
    except httpx.HTTPError as e:
        raise AppException("PM_UNREACHABLE", f"连不上项目管理: {type(e).__name__}", status_code=502)
    if resp.status_code in (401, 403):
        try:
            msg = resp.json().get("error", {}).get("message") or "账号或密码错误"
        except ValueError:
            msg = "账号或密码错误"
        raise AppException("LOGIN_FAILED", msg, status_code=resp.status_code)
    raise AppException("PM_ERROR", f"项目管理返回 HTTP {resp.status_code}", status_code=502)


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        sessions.COOKIE_NAME, token, max_age=sessions.session_hours() * 3600,
        httponly=True, samesite="lax", secure=sessions.cookie_secure(), path="/",
    )


@router.post("/auth/login")
async def login(body: LoginBody, request: Request, response: Response):
    username = body.username.strip()
    ip = request.client.host if request.client else "unknown"
    keys = [f"user:{username.lower()}", f"ip:{ip}"]
    if _limited(keys):
        raise AppException("TOO_MANY_ATTEMPTS", "登录失败次数过多，请 5 分钟后再试", status_code=429)
    try:
        user = await _pm_login(username, body.password)
    except AppException as e:
        if e.code == "LOGIN_FAILED":
            _record_failure(keys)
            logger.info(f"登录失败: {username}")
        raise
    token = await sessions.create(user["id"], user["username"], user.get("display_name") or user["username"])
    _set_cookie(response, token)
    logger.info(f"登录成功: {user['username']}")
    return {"id": user["id"], "username": user["username"], "displayName": user.get("display_name") or user["username"]}


@router.post("/auth/logout")
async def logout(request: Request, response: Response):
    await sessions.delete(request.cookies.get(sessions.COOKIE_NAME))
    response.delete_cookie(sessions.COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/auth/me")
async def me(request: Request):
    u = request.state.user
    return {"id": u["id"], "username": u["username"], "displayName": u["display_name"]}
