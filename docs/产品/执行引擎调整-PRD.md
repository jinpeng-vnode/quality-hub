# 执行引擎调整 产品需求文档（补充）

## 1. 需求背景

### 现状
Quality Hub 原设计集成 Midscene.js 作为 E2E 执行引擎，用例的 `midsceneScript` 字段存储 Midscene DSL。

### 变更原因
- 容器环境已内置 MCP Playwright，AI 可直接操控浏览器完成测试
- Midscene.js 作为中间层不再必要，增加了维护成本
- 需要支持 AI 测试工程师"边测边标记"的工作模式

### 痛点
- Midscene.js 依赖重、调试难
- 无法直接复用 AI 已有的 Playwright 能力
- 缺少手动标记通道，AI 测完还要额外操作

## 2. 目标用户与场景

| 用户 | 场景 |
|------|------|
| AI 测试工程师 | 用 MCP Playwright 手动测试后，通过 API 回写结果到 Quality Hub |
| AI 测试工程师 | 编写 Playwright Python 脚本录入用例，后续自动回归 |
| 项目管理者 | 触发批量回归执行，快速获取通过率报告 |

## 3. 功能描述

### 3.1 手动标记结果

- 通过 API 直接更新单条用例的执行结果
- 接口：`PUT /api/runs/{runId}/results/{resultId}`
- 可设置字段：status（passed/failed/skipped）、errorMessage、duration
- 无需关联脚本，适用于 AI 实时测试场景

### 3.2 Playwright 脚本自动执行

- 用例的 `midsceneScript` 字段复用为存储 Playwright Python 脚本代码（非文件路径）
- 触发执行时，后端逐条处理关联了脚本的用例：
  1. 将脚本内容写入临时 `.py` 文件
  2. 通过 `subprocess` 执行该文件
  3. 退出码 0 = passed，非 0 = failed
  4. 捕获 stdout/stderr 作为 errorMessage
  5. 清理临时文件
- 无脚本的用例自动标记为 skipped

### 3.3 去除 Midscene.js 依赖

- 移除后端中 Midscene.js 相关的执行逻辑
- `midsceneScript` 字段保留，语义变更为"Playwright Python 脚本代码"
- 前端脚本编辑器保留，提示文案改为 Playwright Python

## 4. 验收标准

- [ ] `PUT /api/runs/{runId}/results/{resultId}` 可正常更新用例状态为 passed/failed/skipped
- [ ] 用例 `midsceneScript` 字段可存储 Python 代码并通过 API 读写
- [ ] 触发执行时，有脚本的用例被 subprocess 执行，退出码正确映射为 passed/failed
- [ ] 无脚本用例标记为 skipped
- [ ] 执行失败时 stdout/stderr 被捕获并写入 errorMessage
- [ ] Midscene.js 相关代码和依赖已移除
- [ ] 前端脚本编辑区提示文案更新为 Playwright Python

## 5. 优先级与里程碑

- **优先级**：P1（核心执行流程变更）
- **里程碑**：v0.2 执行引擎重构

## 6. 任务拆分

| Issue | 任务描述 | 负责角色 | 依赖 |
|-------|---------|---------|------|
| TASK-017 | 执行引擎重构（去 Midscene，改 Playwright 脚本 + 手动标记） | 架构师（设计）→ 后端开发（实现） | 无 |

> 架构师设计完成后可进一步拆分为后端子任务。

## 7. 非功能性要求

- 脚本执行超时：单条用例最长 60 秒，超时标记 failed
- 安全：subprocess 执行时限制权限，禁止网络外连（除被测目标）
- 临时文件执行后立即清理

## 8. 风险与备选方案

| 风险 | 影响 | 备选 |
|------|------|------|
| subprocess 执行不稳定 | 结果不可靠 | 加重试机制（最多 1 次） |
| 脚本代码存 DB 体积大 | 数据库膨胀 | 限制单条脚本最大 50KB |
| 字段语义变更 | 旧数据不兼容 | 迁移时清空已有 midsceneScript 内容 |
