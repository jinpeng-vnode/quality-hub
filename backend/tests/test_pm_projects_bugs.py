"""项目只从项目管理导入；失败用例经确认转缺陷"""
from __future__ import annotations

import pytest

from tests.conftest import import_project, insert_run, make_case


def test_manual_create_project_removed(client):
    assert client.post("/api/projects", json={"name": "手动"}).status_code == 405


def test_import_project_from_pm(client, pm):
    r = client.post("/api/projects/import", json={"pmProjectKey": "FLEET", "repoUrl": "https://x/y"})
    assert r.status_code == 200
    p = r.json()
    assert p["pmProjectKey"] == "FLEET" and p["name"] == "FLEET 项目" and p["description"] == "来自项目管理"
    assert pm.calls[-1]["path"] == "/api/projects/FLEET" and pm.calls[-1]["method"] == "GET"
    assert client.post("/api/projects/import", json={"pmProjectKey": "FLEET"}).status_code == 409
    assert client.post("/api/projects/import", json={"pmProjectKey": "fleet"}).status_code == 422
    pm.fail_keys.add("NOPE")
    assert client.post("/api/projects/import", json={"pmProjectKey": "NOPE"}).status_code == 404


def test_project_update_only_repo_url(client):
    pid = import_project(client)
    r = client.put(f"/api/projects/{pid}", json={"name": "改名", "repoUrl": "https://a/b"}).json()
    assert r["name"] == "FLEET 项目" and r["repoUrl"] == "https://a/b"


def test_import_without_pm_config(client, monkeypatch):
    monkeypatch.delenv("PM_BASE")
    r = client.post("/api/projects/import", json={"pmProjectKey": "FLEET"})
    assert r.status_code == 503 and r.json()["code"] == "PM_DISABLED"


@pytest.mark.asyncio
async def test_bug_draft_then_confirm(client, pm):
    pid = import_project(client)
    fid = client.post("/api/features", json={"projectId": pid, "title": "登录", "pmItemKey": "FLEET-12"}).json()["id"]
    a = make_case(client, fid, "密码错误", priority="high")
    b = make_case(client, fid, "登录成功")
    await insert_run(pid, [(a, "failed"), (b, "passed")])
    pm.calls.clear()

    draft = client.get("/api/runs/r1/results/r1-rr0/bug-draft")
    assert draft.status_code == 200
    d = draft.json()
    assert d["severity"] == "major" and "密码错误" in d["title"]
    assert "AssertionError: boom" in d["description"] and "需求 FLEET-12" in d["description"]
    assert pm.calls == []  # 预览不建缺陷

    d["title"] = "测试人员改过的标题"
    r = client.post("/api/runs/r1/results/r1-rr0/bug", json=d)
    assert r.status_code == 200
    bug_key = r.json()["pmBugKey"]
    call = pm.calls[-1]
    assert call["path"] == "/api/projects/FLEET/items"
    assert call["body"] == {"kind": "bug", "title": "测试人员改过的标题", "description": d["description"], "severity": "major"}

    results = client.get("/api/runs/r1/results").json()
    assert {x["id"]: x["pmBugKey"] for x in results}["r1-rr0"] == bug_key
    assert client.post("/api/runs/r1/results/r1-rr0/bug", json=d).status_code == 409
    assert client.get("/api/runs/r1/results/r1-rr1/bug-draft").status_code == 403  # 通过的不能提


def test_bug_rejects_critical(client):
    r = client.post("/api/runs/r1/results/x/bug", json={"title": "t", "severity": "critical"})
    assert r.status_code == 422
