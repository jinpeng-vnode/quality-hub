"""项目管理联动测试：用 httpx.MockTransport 假装项目管理，不连真实 fleet-pm。"""
from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

import app.database as database
from app.integrations import run_report
from app.integrations.pm import PMClient, PMError

FAKE_TOKEN = "fake-token-for-test"


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "qh.db")
    monkeypatch.setenv("PM_BASE", "http://fake-pm")
    monkeypatch.setenv("PM_TOKEN", FAKE_TOKEN)
    monkeypatch.delenv("QH_PUBLIC_URL", raising=False)


class FakePM:
    """记下收到的请求，按需返回错误"""

    def __init__(self, fail_keys: set[str] | None = None):
        self.calls: list[dict] = []
        self.fail_keys = fail_keys or set()

    def handler(self, req: httpx.Request) -> httpx.Response:
        key = req.url.path.split("/")[3]
        self.calls.append({
            "method": req.method, "path": req.url.path,
            "auth": req.headers.get("authorization"), "body": json.loads(req.content),
        })
        if key in self.fail_keys:
            return httpx.Response(404, json={"error": {"code": "not_found", "message": "工作项不存在"}})
        return httpx.Response(200, json={"id": len(self.calls)})

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


def _client():
    from app.main import app
    return TestClient(app)


def _seed(c: TestClient) -> tuple[str, dict[str, str]]:
    pid = c.post("/api/projects", json={"name": "P"}).json()["id"]
    f1 = c.post("/api/features", json={"projectId": pid, "title": "登录", "pmItemKey": "FLEET-12"}).json()
    f2 = c.post("/api/features", json={"projectId": pid, "title": "注册"}).json()
    return pid, {"linked": f1["id"], "plain": f2["id"]}


def _case(c, fid, title):
    body = {"featureId": fid, "title": title, "steps": ["s"], "expectedResult": "ok", "midsceneScript": "print(1)"}
    return c.post("/api/cases", json=body).json()["id"]


async def _make_run(pid: str, results: list[tuple[str, str]]) -> str:
    db = await database.get_db()
    try:
        await db.execute("INSERT INTO runs (id, project_id, status, total) VALUES ('r1', ?, 'passed', ?)", (pid, len(results)))
        for i, (case_id, status) in enumerate(results):
            await db.execute("INSERT INTO run_results (id, run_id, case_id, status) VALUES (?, 'r1', ?, ?)", (f"rr{i}", case_id, status))
        await db.commit()
    finally:
        await db.close()
    return "r1"


def test_feature_pm_item_key_crud():
    with _client() as c:
        pid, f = _seed(c)
        got = c.get(f"/api/features/{f['linked']}").json()
        assert got["pmItemKey"] == "FLEET-12"
        assert got["source"] is None
        assert c.get(f"/api/features/{f['plain']}").json()["pmItemKey"] is None
        assert c.put(f"/api/features/{f['plain']}", json={"pmItemKey": "IDEA-3"}).json()["pmItemKey"] == "IDEA-3"
        assert c.put(f"/api/features/{f['plain']}", json={"title": "注册2"}).json()["pmItemKey"] == "IDEA-3"
        assert c.put(f"/api/features/{f['plain']}", json={"pmItemKey": ""}).json()["pmItemKey"] is None
        assert c.post("/api/features", json={"projectId": pid, "title": "x", "pmItemKey": "fleet12"}).status_code == 422


def test_build_comment_counts_and_rate():
    rows = [
        {"status": "passed", "case_title": "a"},
        {"status": "failed", "case_title": "b"},
        {"status": "skipped", "case_title": "c"},
        {"status": "passed", "case_title": "d"},
    ]
    text = run_report.build_comment("p1", "r1", rows)
    assert "用例 4 条：通过 2、失败 1、跳过 1；通过率 66.7%" in text
    assert "- b" in text
    assert "执行详情：/projects/p1/runs/r1" in text


def test_build_comment_all_skipped():
    text = run_report.build_comment("p", "r", [{"status": "skipped", "case_title": "a"}])
    assert "通过率 无（全部跳过）" in text


@pytest.mark.asyncio
async def test_report_run_posts_only_linked_features():
    with _client() as c:
        pid, f = _seed(c)
        a = _case(c, f["linked"], "登录成功")
        b = _case(c, f["linked"], "密码错误")
        d = _case(c, f["plain"], "注册成功")
    run_id = await _make_run(pid, [(a, "passed"), (b, "failed"), (d, "failed")])
    pm = FakePM()
    outcome = await run_report.report_run(run_id, transport=pm.transport)
    assert outcome == {"FLEET-12": "ok"}
    assert len(pm.calls) == 1
    call = pm.calls[0]
    assert call["method"] == "POST" and call["path"] == "/api/items/FLEET-12/comments"
    assert call["auth"] == f"Bearer {FAKE_TOKEN}"
    assert "通过 1、失败 1、跳过 0；通过率 50.0%" in call["body"]["body"]
    assert "密码错误" in call["body"]["body"] and "注册成功" not in call["body"]["body"]


@pytest.mark.asyncio
async def test_report_run_disabled_without_env(monkeypatch):
    monkeypatch.delenv("PM_TOKEN")
    pm = FakePM()
    assert await run_report.report_run("r1", transport=pm.transport) == {}
    assert pm.calls == []


@pytest.mark.asyncio
async def test_report_run_error_is_recorded_and_token_not_leaked():
    with _client() as c:
        pid, f = _seed(c)
        a = _case(c, f["linked"], "登录成功")
    run_id = await _make_run(pid, [(a, "passed")])
    outcome = await run_report.report_run(run_id, transport=FakePM(fail_keys={"FLEET-12"}).transport)
    assert "404" in outcome["FLEET-12"] and "not_found" in outcome["FLEET-12"]
    assert FAKE_TOKEN not in outcome["FLEET-12"]


@pytest.mark.asyncio
async def test_client_raises_pm_error():
    client = PMClient("http://fake-pm", FAKE_TOKEN, FakePM(fail_keys={"X-1"}).transport)
    with pytest.raises(PMError) as e:
        await client.add_comment("X-1", "hi")
    assert e.value.status == 404 and FAKE_TOKEN not in str(e.value)
