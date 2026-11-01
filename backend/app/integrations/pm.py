"""backend/app/integrations/pm.py — 项目管理（pm-server）出站客户端

quality-hub 对项目管理的所有调用都收在这里，路由层不直接拼请求。
配置只从环境变量读：
- PM_BASE：项目管理地址，如 http://fleet-pm:8930
- PM_TOKEN：项目管理机器人令牌（tester 角色），不写进代码、不进日志
两者任一没配，客户端视为未启用，所有调用直接返回 None。
"""
from __future__ import annotations

import os

import httpx
from loguru import logger


class PMError(Exception):
    """项目管理接口返回错误（只带状态码和对方的错误码，不带令牌）"""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(f"项目管理返回 {status} {code}: {message}")
        self.status = status
        self.code = code


class PMClient:
    def __init__(self, base: str, token: str, transport: httpx.AsyncBaseTransport | None = None):
        self._base = base.rstrip("/")
        self._token = token
        self._transport = transport

    @classmethod
    def from_env(cls, transport: httpx.AsyncBaseTransport | None = None) -> "PMClient | None":
        base = os.environ.get("PM_BASE", "").strip()
        token = os.environ.get("PM_TOKEN", "").strip()
        if not base or not token:
            return None
        return cls(base, token, transport)

    async def _request(self, method: str, path: str, json: dict | None = None) -> dict:
        headers = {"Authorization": f"Bearer {self._token}"}
        async with httpx.AsyncClient(base_url=self._base, transport=self._transport, timeout=15) as c:
            resp = await c.request(method, path, json=json, headers=headers)
        if resp.status_code >= 400:
            try:
                err = resp.json().get("error", {})
            except ValueError:
                err = {}
            raise PMError(resp.status_code, err.get("code", ""), err.get("message", resp.text[:200]))
        return resp.json()

    async def add_comment(self, item_key: str, body: str) -> int:
        """在工作项下发一条评论，返回评论 id。接口：POST /api/items/{key}/comments"""
        data = await self._request("POST", f"/api/items/{item_key}/comments", json={"body": body})
        logger.info(f"项目管理评论已写入: {item_key} (comment={data.get('id')})")
        return data["id"]

    async def get_project(self, project_key: str) -> dict:
        """读项目：GET /api/projects/{key}，返回 key、name、description 等"""
        return await self._request("GET", f"/api/projects/{project_key}")

    async def create_bug(self, project_key: str, title: str, description: str, severity: str) -> dict:
        """建缺陷：POST /api/projects/{key}/items，kind=bug，返回工作项（含 key）"""
        body = {"kind": "bug", "title": title, "description": description, "severity": severity}
        data = await self._request("POST", f"/api/projects/{project_key}/items", json=body)
        logger.info(f"项目管理缺陷已建: {data.get('key')}")
        return data


def require_client() -> PMClient:
    """要用项目管理时调用；没配 PM_BASE / PM_TOKEN 就报 503"""
    from app.utils.exceptions import AppException

    client = PMClient.from_env(_transport_override)
    if client is None:
        raise AppException("PM_DISABLED", "未配置项目管理（PM_BASE、PM_TOKEN）", status_code=503)
    return client


# 测试用：替换出站传输层，换成假的项目管理
_transport_override: httpx.AsyncBaseTransport | None = None


def set_transport_for_test(transport: httpx.AsyncBaseTransport | None) -> None:
    global _transport_override
    _transport_override = transport


def pm_error_to_app(e: Exception):
    """把项目管理的错误转成 quality-hub 的统一错误（502），不带令牌"""
    from app.utils.exceptions import AppException

    if isinstance(e, PMError):
        status = 404 if e.status == 404 else 502
        return AppException("PM_ERROR", str(e), status_code=status)
    return AppException("PM_UNREACHABLE", f"连不上项目管理: {type(e).__name__}", status_code=502)
