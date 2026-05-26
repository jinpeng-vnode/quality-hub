---
创建时间：2026-05-26 17:35
最后更新：2026-05-26 17:35
状态：设计中
---

# L2-TASK-017 执行引擎重构 设计文档

## 1. 需求摘要

去掉 Midscene.js 依赖，执行引擎改为两种模式：
- **手动标记（manual）**：AI 测试工程师通过 PUT API 逐条回写用例执行结果
- **脚本执行（script）**：后端串行执行用例关联的 Playwright Python 脚本，通过 asyncio.subprocess 运行

核心约束：单条超时 60s、串行执行、无脚本用例标记 skipped、临时文件执行后清理。

## 2. 方案选择

| 方案 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| asyncio.subprocess + 临时文件 | 进程隔离、无新依赖、超时可控 | 串行性能一般 | ✅ 选用 |
| Celery 任务队列 | 并发好、可重试 | 引入 Redis/RabbitMQ，过度设计 | ❌ |
| 直接 exec() 执行脚本 | 无进程开销 | 不隔离、无超时控制、安全风险 | ❌ |

**选择理由**：项目规模小，串行执行足够。asyncio.subprocess 原生支持超时，进程隔离保证主进程稳定，不引入新依赖。

## 3. 文件结构

### 后端变更文件

```
backend/app/
├── routers/
│   └── runs.py              # 修改：新增 PUT 手动标记接口、create_run 支持 mode
├── services/
│   └── script_runner.py     # 新增：脚本执行引擎（替代 midscene_runner.py）
├── models/
│   └── schemas.py           # 修改：RunCreate 加 mode、RunResultOut 加 log、新增 RunResultUpdate
└── database.py              # 修改：cases 加 midscene_script、runs 加 mode、run_results 加 log
```

### 前端变更文件

```
frontend/src/
├── types/index.ts           # 修改：Execution 加 mode、ExecutionResult 加 log、TestCase 加 midsceneScript
├── views/
│   ├── ExecutionView.vue    # 修改：触发执行时选择模式、详情显示日志
│   └── TestCaseView.vue     # 修改：用例表单增加脚本编辑区
└── api/index.ts             # 修改：API 路径从 /executions 对齐到 /runs
```

## 4. 类型定义

### 后端 Pydantic 模型（Python）

```python
# --- schemas.py 新增/修改 ---

class RunCreate(BaseModel):
    project_id: str = Field(..., alias="projectId")
    case_ids: list[str] = Field(default_factory=list, alias="caseIds")
    mode: str = Field(default="manual")  # "manual" | "script"

    model_config = {"populate_by_name": True}


class RunResultUpdate(BaseModel):
    """手动标记单条结果"""
    status: str = Field(...)  # "passed" | "failed" | "skipped"
    error_message: str = Field(default="", alias="errorMessage")
    duration_ms: int = Field(default=0, alias="durationMs")

    model_config = {"populate_by_name": True}


class RunResultOut(BaseModel):
    id: str
    case_id: str = Field(alias="caseId")
    status: str
    error_message: str = Field(alias="errorMessage", default="")
    duration_ms: int = Field(alias="durationMs", default=0)
    log: str = Field(default="")  # 新增：脚本 stdout/stderr

    model_config = {"populate_by_name": True}


class RunOut(BaseModel):
    id: str
    project_id: str = Field(alias="projectId")
    status: str
    mode: str = Field(default="manual")  # 新增
    total: int
    passed: int
    failed: int
    skipped: int
    started_at: str | None = Field(alias="startedAt", default=None)
    finished_at: str | None = Field(alias="finishedAt", default=None)
    created_at: str = Field(alias="createdAt", default="")

    model_config = {"populate_by_name": True}


class CaseCreate(BaseModel):
    feature_id: str = Field(..., alias="featureId")
    title: str = Field(..., min_length=1, max_length=300)
    steps: list[str] = Field(default_factory=list)
    expected: str = Field(default="")
    priority: str = Field(default="medium")
    midscene_script: str = Field(default="", alias="midsceneScript")  # 新增

    model_config = {"populate_by_name": True}


class CaseUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    steps: list[str] | None = None
    expected: str | None = None
    priority: str | None = None
    status: str | None = None
    midscene_script: str | None = Field(default=None, alias="midsceneScript")  # 新增

    model_config = {"populate_by_name": True}


class CaseOut(BaseModel):
    id: str
    feature_id: str = Field(alias="featureId")
    title: str
    steps: list[str]
    expected: str
    priority: str
    status: str
    midscene_script: str = Field(alias="midsceneScript", default="")  # 新增
    created_at: str = Field(alias="createdAt", default="")
    updated_at: str = Field(alias="updatedAt", default="")

    model_config = {"populate_by_name": True}
```

### 前端 TypeScript 类型

```typescript
// --- types/index.ts 修改 ---

export interface TestCase {
  id: string
  featureId: string
  title: string
  steps: string[]
  expected: string
  priority: string
  status: string
  midsceneScript: string  // 新增：Playwright Python 脚本代码
  createdAt: string
  updatedAt: string
}

export interface Execution {
  id: string
  projectId: string
  mode: 'manual' | 'script'  // 新增
  status: 'pending' | 'running' | 'completed'
  total: number
  passed: number
  failed: number
  skipped: number
  startedAt: string | null
  finishedAt: string | null
  createdAt: string
}

export interface ExecutionResult {
  id: string
  caseId: string
  status: 'pending' | 'passed' | 'failed' | 'skipped'
  errorMessage: string
  durationMs: number
  log: string  // 新增：脚本输出日志
}
```

## 5. 外部接口

| 方法 | 路径 | 请求体 | 响应体 | 说明 |
|------|------|--------|--------|------|
| POST | `/api/runs` | `RunCreate` | `RunOut` | 创建执行记录；mode=script 时后台异步执行脚本 |
| GET | `/api/runs` | query: `projectId` | `RunOut[]` | 获取执行记录列表 |
| GET | `/api/runs/{runId}/report` | — | `RunReportOut` | 获取执行报告（含每条结果） |
| PUT | `/api/runs/{runId}/results/{resultId}` | `RunResultUpdate` | `RunResultOut` | 手动标记单条结果（仅 mode=manual 时可用） |
| POST | `/api/cases` | `CaseCreate` | `CaseOut` | 创建用例（含 midsceneScript） |
| PUT | `/api/cases/{caseId}` | `CaseUpdate` | `CaseOut` | 更新用例（含 midsceneScript） |

### PUT /api/runs/{runId}/results/{resultId} 详细说明

- 仅当 run.mode == "manual" 时允许调用，否则返回 403
- 更新 status、error_message、duration_ms
- 每次更新后重新计算 run 的 passed/failed/skipped 计数
- 当所有 results 都不是 pending 时，自动将 run.status 设为 completed

### POST /api/runs 执行逻辑变更

```
mode=manual:
  1. 创建 run 记录（status=running）
  2. 创建 run_results（status=pending）
  3. 返回 run（等待外部通过 PUT 逐条标记）

mode=script:
  1. 创建 run 记录（status=running）
  2. 创建 run_results（status=pending）
  3. 启动后台任务 asyncio.create_task(execute_script_run(...))
  4. 返回 run（前端轮询状态）
```

## 6. 模块依赖

```
runs.py (路由层)
  ├── schemas.py (数据模型)
  ├── database.py (数据库)
  └── script_runner.py (脚本执行引擎)
        └── asyncio.subprocess (标准库)

ExecutionView.vue (前端)
  ├── api/index.ts → /api/runs
  └── types/index.ts
```

## 7. 错误处理

| 场景 | HTTP 状态码 | 错误信息 | 前端展示 |
|------|------------|---------|---------|
| run 不存在 | 404 | "执行记录不存在" | message.error |
| result 不存在 | 404 | "执行结果不存在" | message.error |
| 手动标记非 manual 模式的 run | 403 | "仅手动模式可标记结果" | message.error |
| 脚本执行超时（60s） | — | 内部标记 failed，log 记录 "执行超时" | 详情页显示 |
| 脚本执行异常（非零退出码） | — | 内部标记 failed，log 记录 stderr | 详情页显示 |
| 用例无脚本（mode=script） | — | 内部标记 skipped，log 为空 | 详情页显示 skipped |
| 项目不存在 | 404 | "项目不存在" | message.error |

## 8. 模块分配表

| 模块/文件 | 负责角色 | 层级 | 依赖 |
|-----------|---------|------|------|
| `backend/app/services/script_runner.py` | 后端开发 | L2 | 无 |
| `backend/app/routers/runs.py` | 后端开发 | L2 | script_runner.py |
| `backend/app/models/schemas.py` | 后端开发 | L2 | 无 |
| `backend/app/database.py` | 后端开发 | L2 | 无 |
| `backend/app/routers/cases.py` | 后端开发 | L2 | schemas.py |
| `frontend/src/types/index.ts` | 前端开发 | L2 | 后端接口定义 |
| `frontend/src/api/index.ts` | 前端开发 | L2 | 无 |
| `frontend/src/views/ExecutionView.vue` | 前端开发 | L2 | types, api |
| `frontend/src/views/TestCaseView.vue` | 前端开发 | L2 | types, api |

## 9. 开发层级

### L2 — 后端开发（可并行）

1. **数据库 schema 变更** — database.py 加字段
2. **schemas.py 模型更新** — 新增 RunResultUpdate、修改 RunCreate/CaseCreate/CaseOut
3. **script_runner.py** — 脚本执行引擎核心逻辑
4. **runs.py 路由重构** — PUT 手动标记 + create_run mode 分支
5. **cases.py 路由更新** — 支持 midscene_script 字段读写

### L2 — 前端开发（依赖后端接口定义）

1. **types/index.ts** — 类型更新
2. **api/index.ts** — 路径从 /executions 改为 /runs
3. **ExecutionView.vue** — 模式选择 + 日志展示
4. **TestCaseView.vue** — 脚本编辑区

## 10. 依赖清单

| 包名 | 版本 | 用途 | 环境 |
|------|------|------|------|
| asyncio (标准库) | — | subprocess 异步执行 | 后端 |
| tempfile (标准库) | — | 临时脚本文件管理 | 后端 |
| playwright | 已安装 | 被脚本调用（非后端直接依赖） | 容器 |

**无新增外部依赖。**

## 11. 开发者备注

### script_runner.py 核心逻辑伪代码

```python
import asyncio
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone

async def execute_script_run(run_id: str, case_scripts: list[dict]) -> None:
    """后台执行脚本任务，串行处理每条用例"""
    db = await get_db()
    try:
        for item in case_scripts:
            result_id = item["result_id"]
            script = item["script"]

            if not script:
                # 无脚本，标记 skipped
                await _update_result(db, result_id, "skipped", "", 0, "")
                continue

            start = datetime.now(timezone.utc)
            status, log = await _run_single_script(script)
            duration = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
            error_msg = log if status == "failed" else ""
            await _update_result(db, result_id, status, error_msg, duration, log)

        # 更新 run 汇总
        await _finalize_run(db, run_id)
    finally:
        await db.close()


async def _run_single_script(script: str) -> tuple[str, str]:
    """执行单条脚本，返回 (status, log)"""
    tmp_dir = tempfile.mkdtemp(prefix="qh_run_")
    script_path = Path(tmp_dir) / "test_script.py"
    try:
        script_path.write_text(script, encoding="utf-8")
        proc = await asyncio.create_subprocess_exec(
            "python3", str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tmp_dir,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        log = (stdout.decode() + "\n" + stderr.decode()).strip()
        status = "passed" if proc.returncode == 0 else "failed"
        return status, log
    except asyncio.TimeoutError:
        proc.kill()
        return "failed", "执行超时（60s）"
    except Exception as e:
        return "failed", f"执行异常: {e}"
    finally:
        # 清理临时目录
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
```

### 数据库 DDL 变更

```sql
-- cases 表新增字段
ALTER TABLE cases ADD COLUMN midscene_script TEXT DEFAULT '';

-- runs 表新增字段
ALTER TABLE runs ADD COLUMN mode TEXT NOT NULL DEFAULT 'manual';

-- run_results 表新增字段
ALTER TABLE run_results ADD COLUMN log TEXT DEFAULT '';
```

### 前端 API 路径对齐

当前前端 ExecutionView 调用 `/executions`，需统一改为 `/runs`：
- `GET /api/runs?projectId=xxx` — 列表
- `POST /api/runs` — 触发执行
- `GET /api/runs/{runId}/report` — 详情（含 results）

### 手动标记完成检测逻辑

每次 PUT 更新 result 后：
1. 查询该 run 下所有 results 的 status
2. 重新计算 passed/failed/skipped 计数并更新 run
3. 如果没有 pending 状态的 result，将 run.status 设为 completed，记录 finished_at
