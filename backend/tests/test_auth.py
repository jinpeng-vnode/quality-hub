"""登录与唯一鉴权关口"""
from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import WEBHOOK_SECRET  # noqa: F401  (确保 env 夹具生效)


def test_unauthenticated_business_api_401(anon):
    for method, path in [("GET", "/api/projects"), ("GET", "/api/runs?projectId=x"),
                         ("POST", "/api/projects/import"), ("GET", "/api/auth/me"), ("GET", "/docs")]:
        r = anon.request(method, path, json={} if method == "POST" else None)
        assert r.status_code == 401, (path, r.status_code)
        if path.startswith("/api"):
            assert r.json()["code"] == "UNAUTHORIZED"


def test_public_paths(anon):
    assert anon.get("/health").json() == {"status": "ok"}
    r = anon.post("/api/integrations/pm/webhook", content=b"{}", headers={"X-PM-Signature": "sha256=bad"})
    assert r.status_code == 401 and r.json()["message"] == "webhook 签名校验失败"


def test_login_me_logout(anon, pm):
    r = anon.post("/api/auth/login", json={"username": "tester", "password": "right-password"})
    assert r.status_code == 200 and r.json()["displayName"] == "测试员"
    set_cookie = r.headers["set-cookie"]
    assert "qh_session=" in set_cookie and "HttpOnly" in set_cookie and "samesite=lax" in set_cookie.lower()
    assert "Secure" not in set_cookie
    assert pm.logout_cookie == "pm_session=pm-sess-abc"  # 项目管理那边的会话已注销
    assert pm.calls[0]["body"]["password"] == "***"
    assert anon.get("/api/auth/me").json()["username"] == "tester"
    assert anon.get("/api/projects").status_code == 200
    assert anon.post("/api/auth/logout").json() == {"ok": True}
    assert anon.get("/api/projects").status_code == 401


def test_cookie_secure_by_env(anon, monkeypatch):
    monkeypatch.setenv("QH_COOKIE_SECURE", "1")
    r = anon.post("/api/auth/login", json={"username": "tester", "password": "right-password"})
    assert "Secure" in r.headers["set-cookie"]


def test_wrong_password_and_bot(anon):
    r = anon.post("/api/auth/login", json={"username": "tester", "password": "x"})
    assert r.status_code == 401 and r.json()["code"] == "LOGIN_FAILED"
    assert "x" not in r.json()["message"].replace("账号或密码错误", "")
    r = anon.post("/api/auth/login", json={"username": "bot", "password": "right-password"})
    assert r.status_code == 403 and "机器人" in r.json()["message"]


def test_logout_pm_failure_still_logs_in(anon, pm):
    pm.logout_status = 500
    r = anon.post("/api/auth/login", json={"username": "tester", "password": "right-password"})
    assert r.status_code == 200


def test_rate_limit(anon):
    for _ in range(5):
        assert anon.post("/api/auth/login", json={"username": "tester", "password": "bad"}).status_code == 401
    r = anon.post("/api/auth/login", json={"username": "tester", "password": "right-password"})
    assert r.status_code == 429


def test_no_pm_base_login_503(anon, monkeypatch):
    monkeypatch.delenv("PM_BASE")
    r = anon.post("/api/auth/login", json={"username": "tester", "password": "right-password"})
    assert r.status_code == 503 and r.json()["code"] == "PM_DISABLED"


def test_csrf_required_for_writes(client):
    from app.main import app
    jar = client.cookies
    with TestClient(app, cookies=jar) as c:  # 有会话但不带 X-Requested-With
        assert c.get("/api/projects").status_code == 200
        r = c.post("/api/projects/import", json={"pmProjectKey": "FLEET"})
        assert r.status_code == 403 and r.json()["code"] == "CSRF"


def test_expired_session(client, monkeypatch):
    import asyncio
    import app.database as database

    async def expire():
        db = await database.get_db()
        await db.execute("UPDATE sessions SET expires_at = '2000-01-01T00:00:00+00:00'")
        await db.commit()
        await db.close()
    asyncio.run(expire())
    assert client.get("/api/projects").status_code == 401
