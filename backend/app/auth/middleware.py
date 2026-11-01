"""backend/app/auth/middleware.py — 唯一的鉴权关口

所有请求都经过这里：放行名单之外，没有有效会话一律 401；
带会话的写请求（非 GET/HEAD/OPTIONS）还要带请求头 X-Requested-With: qh（防 CSRF）。
各路由文件不再各自判断登录。
"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from app.auth import sessions

CSRF_HEADER = "x-requested-with"
CSRF_VALUE = "qh"

# 不要登录的路径：健康检查、登录 / 退出、项目管理 webhook（接口内部自己做 HMAC 校验）
PUBLIC_PATHS = {
    "/health",
    "/api/auth/login",
    "/api/auth/logout",
    "/api/integrations/pm/webhook",
}
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _error(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message, "detail": None})


async def require_auth(request: Request, call_next):
    path = request.url.path
    if path == "/api/integrations/pm/webhook":
        return await call_next(request)
    if request.method not in _SAFE_METHODS and request.headers.get(CSRF_HEADER) != CSRF_VALUE:
        return _error(403, "CSRF", "缺少请求头 X-Requested-With: qh")
    if path in PUBLIC_PATHS:
        return await call_next(request)
    user = await sessions.lookup(request.cookies.get(sessions.COOKIE_NAME))
    if user is None:
        return _error(401, "UNAUTHORIZED", "请先登录")
    request.state.user = user
    return await call_next(request)
