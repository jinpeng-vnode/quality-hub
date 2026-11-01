"""项目管理 webhook：签名校验、缺陷进测试标待回归、部署跑冒烟"""
from __future__ import annotations

import hashlib
import hmac
import json

import pytest

import app.routers.runs as runs_mod
from tests.conftest import WEBHOOK_SECRET, import_project, insert_run, make_case


def _post(c, payload: dict, secret: str = WEBHOOK_SECRET):
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return c.post("/api/integrations/pm/webhook", content=body,
                  headers={"Content-Type": "application/json", "X-PM-Signature": sig})


@pytest.fixture
def no_exec(monkeypatch):
    """冒烟 run 只建记录，不真的跑脚本"""
    async def fake(*_a, **_k):
        return None
    monkeypatch.setattr(runs_mod, "_execute_script_run", fake)


def test_signature_required(client, monkeypatch):
    assert _post(client, {"event": "item.created"}, secret="wrong").status_code == 401
    r = client.post("/api/integrations/pm/webhook", json={"event": "item.created"})
    assert r.status_code == 401
    monkeypatch.delenv("PM_WEBHOOK_SECRET")
    assert _post(client, {"event": "item.created"}).status_code == 401
    monkeypatch.setenv("PM_WEBHOOK_SECRET", WEBHOOK_SECRET)
    assert _post(client, {"event": "item.created"}).json() == {"ok": True, "handled": None}


@pytest.mark.asyncio
async def test_bug_to_testing_marks_regression_and_retry_clears(client, no_exec):
    pid = import_project(client)
    fid = client.post("/api/features", json={"projectId": pid, "title": "登录"}).json()["id"]
    a = make_case(client, fid, "密码错误")
    await insert_run(pid, [(a, "failed")])
    draft = client.get("/api/runs/r1/results/r1-rr0/bug-draft").json()
    bug = client.post("/api/runs/r1/results/r1-rr0/bug", json=draft).json()["pmBugKey"]

    ev = {"event": "item.transitioned", "project": {"key": "FLEET"},
          "item": {"key": bug, "kind": "bug", "status": "testing"},
          "transition": {"from": "fixing", "to": "testing"}}
    assert _post(client, ev).json()["marked"] == 1
    res = client.get("/api/runs/r1/results").json()[0]
    assert res["regressionPending"] is True

    client.put("/api/runs/r1/results/r1-rr0", json={"status": "passed"})
    assert client.get("/api/runs/r1/results").json()[0]["regressionPending"] is False

    ev["transition"]["to"] = "deploying"
    assert _post(client, ev).json()["handled"] is None


def test_deployment_runs_smoke_once(client, no_exec):
    pid = import_project(client)
    fid = client.post("/api/features", json={"projectId": pid, "title": "登录"}).json()["id"]
    s1 = make_case(client, fid, "冒烟一", smoke=True)
    make_case(client, fid, "普通用例")
    ev = {"event": "deployment.created", "project": {"key": "FLEET"},
          "item": {"key": "FLEET-12"}, "data": {"deploy_no": "Jenkins #9", "environment": "线上"}}
    r = _post(client, ev).json()
    assert r["handled"] == "smoke" and r["runId"]
    results = client.get(f"/api/runs/{r['runId']}/results").json()
    assert [x["caseId"] for x in results] == [s1]
    assert _post(client, ev).json()["runId"] is None  # 同一个部署编号不重复跑
    ev["project"]["key"] = "OTHER"
    assert _post(client, ev).json()["runId"] is None
