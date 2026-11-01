"""公共夹具：临时数据库 + 假的项目管理（httpx.MockTransport），不连真实 fleet-pm。"""
from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

import app.database as database
from app.integrations import pm as pm_mod

FAKE_TOKEN = "fake-token-for-test"
WEBHOOK_SECRET = "fake-webhook-secret"


class FakePM:
    """记下收到的请求；fail_keys 里的项目或工作项返回 404"""

    def __init__(self):
        self.calls: list[dict] = []
        self.fail_keys: set[str] = set()
        self.bug_seq = 100
        self.logout_cookie: str | None = None
        self.logout_status = 200

    def handler(self, req: httpx.Request) -> httpx.Response:
        parts = req.url.path.strip("/").split("/")  # api, projects|items, key, ...
        body = json.loads(req.content) if req.content else None
        self.calls.append({"method": req.method, "path": req.url.path,
                           "auth": req.headers.get("authorization"), "body": body})
        if req.url.path == "/api/auth/login":
            self.calls[-1]["body"] = {"username": body["username"], "password": "***"}
            if req.headers.get("x-requested-with") != "pm":
                return httpx.Response(403, json={"error": {"code": "forbidden", "message": "缺少 CSRF 头"}})
            if body["username"] == "bot":
                return httpx.Response(403, json={"error": {"code": "forbidden", "message": "机器人账号不能在网页登录，请用 API 令牌"}})
            if body["password"] != "right-password":
                return httpx.Response(401, json={"error": {"code": "unauthorized", "message": "账号或密码错误"}})
            return httpx.Response(200, json={"id": 7, "username": body["username"], "display_name": "测试员"},
                                  headers={"set-cookie": "pm_session=pm-sess-abc; Path=/; HttpOnly"})
        if req.url.path == "/api/auth/logout":
            self.logout_cookie = req.headers.get("cookie")
            return httpx.Response(self.logout_status, json={"ok": True})
        key = parts[2] if len(parts) > 2 else ""
        if key in self.fail_keys:
            return httpx.Response(404, json={"error": {"code": "not_found", "message": "不存在"}})
        if parts[1] == "projects" and len(parts) == 3 and req.method == "GET":
            return httpx.Response(200, json={"id": 1, "key": key, "name": f"{key} 项目", "description": "来自项目管理"})
        if parts[1] == "projects" and parts[-1] == "items" and req.method == "POST":
            self.bug_seq += 1
            return httpx.Response(200, json={"key": f"{key}-{self.bug_seq}", "kind": "bug"})
        if parts[1] == "items" and parts[-1] == "comments":
            return httpx.Response(200, json={"id": len(self.calls)})
        return httpx.Response(404, json={"error": {"code": "not_found", "message": "假接口没有这条路由"}})

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


@pytest.fixture(autouse=True)
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "qh.db")
    monkeypatch.setenv("PM_BASE", "http://fake-pm")
    monkeypatch.setenv("PM_TOKEN", FAKE_TOKEN)
    monkeypatch.setenv("PM_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.delenv("QH_PUBLIC_URL", raising=False)


@pytest.fixture
def pm():
    fake = FakePM()
    pm_mod.set_transport_for_test(fake.transport)
    yield fake
    pm_mod.set_transport_for_test(None)


@pytest.fixture
def anon(pm):
    """没登录的客户端（带 CSRF 头）"""
    from app.auth.routes import reset_rate_limit
    from app.main import app
    reset_rate_limit()
    with TestClient(app, headers={"X-Requested-With": "qh"}) as c:
        yield c


@pytest.fixture
def client(anon):
    """已登录的客户端"""
    r = anon.post("/api/auth/login", json={"username": "tester", "password": "right-password"})
    assert r.status_code == 200, r.text
    yield anon


def import_project(c: TestClient, key: str = "FLEET") -> str:
    r = c.post("/api/projects/import", json={"pmProjectKey": key})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def make_case(c: TestClient, fid: str, title: str, priority: str = "medium", smoke: bool = False) -> str:
    body = {"featureId": fid, "title": title, "steps": ["s"], "expectedResult": "ok",
            "midsceneScript": "print(1)", "priority": priority, "smoke": smoke}
    r = c.post("/api/cases", json=body)
    assert r.status_code == 200, r.text
    return r.json()["id"]


async def insert_run(pid: str, results: list[tuple[str, str]], run_id: str = "r1") -> str:
    db = await database.get_db()
    try:
        await db.execute("INSERT INTO runs (id, project_id, status, total) VALUES (?, ?, 'failed', ?)",
                         (run_id, pid, len(results)))
        for i, (case_id, status) in enumerate(results):
            await db.execute(
                "INSERT INTO run_results (id, run_id, case_id, status, error_message) VALUES (?, ?, ?, ?, ?)",
                (f"{run_id}-rr{i}", run_id, case_id, status, "AssertionError: boom" if status == "failed" else ""),
            )
        await db.commit()
    finally:
        await db.close()
    return run_id
