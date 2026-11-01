"""功能点关联需求、run 结束写需求评论"""
from __future__ import annotations

import pytest

from app.integrations import run_report
from app.integrations.pm import PMClient, PMError
from tests.conftest import FAKE_TOKEN, FakePM, import_project, insert_run, make_case


def _features(c, pid):
    f1 = c.post("/api/features", json={"projectId": pid, "title": "登录", "pmItemKey": "FLEET-12"}).json()
    f2 = c.post("/api/features", json={"projectId": pid, "title": "注册"}).json()
    return f1["id"], f2["id"]


def test_feature_pm_item_key_crud(client):
    pid = import_project(client)
    linked, plain = _features(client, pid)
    got = client.get(f"/api/features/{linked}").json()
    assert got["pmItemKey"] == "FLEET-12" and got["source"] is None
    assert client.get(f"/api/features/{plain}").json()["pmItemKey"] is None
    assert client.put(f"/api/features/{plain}", json={"pmItemKey": "IDEA-3"}).json()["pmItemKey"] == "IDEA-3"
    assert client.put(f"/api/features/{plain}", json={"title": "注册2"}).json()["pmItemKey"] == "IDEA-3"
    assert client.put(f"/api/features/{plain}", json={"pmItemKey": ""}).json()["pmItemKey"] is None
    assert client.post("/api/features", json={"projectId": pid, "title": "x", "pmItemKey": "fleet12"}).status_code == 422


def test_build_comment_counts_and_rate():
    rows = [{"status": s, "case_title": t} for s, t in
            [("passed", "a"), ("failed", "b"), ("skipped", "c"), ("passed", "d")]]
    text = run_report.build_comment("p1", "r1", rows)
    assert "用例 4 条：通过 2、失败 1、跳过 1；通过率 66.7%" in text
    assert "- b" in text and "执行详情：/projects/p1/runs/r1" in text
    assert "通过率 无（全部跳过）" in run_report.build_comment("p", "r", [{"status": "skipped", "case_title": "a"}])


@pytest.mark.asyncio
async def test_report_run_posts_only_linked_features(client, pm):
    pid = import_project(client)
    linked, plain = _features(client, pid)
    a, b = make_case(client, linked, "登录成功"), make_case(client, linked, "密码错误")
    d = make_case(client, plain, "注册成功")
    pm.calls.clear()
    run_id = await insert_run(pid, [(a, "passed"), (b, "failed"), (d, "failed")])
    assert await run_report.report_run(run_id) == {"FLEET-12": "ok"}
    assert len(pm.calls) == 1
    call = pm.calls[0]
    assert call["method"] == "POST" and call["path"] == "/api/items/FLEET-12/comments"
    assert call["auth"] == f"Bearer {FAKE_TOKEN}"
    assert "通过 1、失败 1、跳过 0；通过率 50.0%" in call["body"]["body"]
    assert "密码错误" in call["body"]["body"] and "注册成功" not in call["body"]["body"]


@pytest.mark.asyncio
async def test_report_run_disabled_without_env(monkeypatch, pm):
    monkeypatch.delenv("PM_TOKEN")
    assert await run_report.report_run("r1") == {}
    assert pm.calls == []


@pytest.mark.asyncio
async def test_report_run_error_recorded_without_token(client, pm):
    pid = import_project(client)
    linked, _ = _features(client, pid)
    a = make_case(client, linked, "登录成功")
    run_id = await insert_run(pid, [(a, "passed")])
    pm.fail_keys.add("FLEET-12")
    outcome = await run_report.report_run(run_id)
    assert "404" in outcome["FLEET-12"] and FAKE_TOKEN not in outcome["FLEET-12"]


@pytest.mark.asyncio
async def test_client_raises_pm_error():
    fake = FakePM()
    fake.fail_keys.add("X-1")
    with pytest.raises(PMError) as e:
        await PMClient("http://fake-pm", FAKE_TOKEN, fake.transport).add_comment("X-1", "hi")
    assert e.value.status == 404 and FAKE_TOKEN not in str(e.value)
