# quality-hub 与项目管理联动方案

> 状态：草案，只读调研后起草，不含代码改动。日期 2026-11-01。
> 依据：quality-hub `origin/dev` 4139095（backend/app、frontend/src），项目管理 `jinpeng-vnode/project-manager` `origin/dev` 023fdbe（server/src、server/migrations）。
> 本文涉及的接口都是两边代码里现有的路由；标「需新增」的是要改代码的地方，改之前要先定。

## 一、两边各管什么

| | quality-hub（质量） | 项目管理（pm-server / pm-mcp） |
|---|---|---|
| 定位 | 测试人员的工作台：功能点、测试用例、Playwright/Midscene 脚本执行、通过率和覆盖率 | 研发流程：需求 → 任务 → 缺陷，状态机加卡口，关联提交和部署 |
| 主要对象 | project、feature（功能点）、case（用例）、run（一次执行）、run_result（单条结果） | project（key，如 FLEET）、work_item（requirement / bug / task）、commit、deployment、comment、attachment |
| 存储 | SQLite `backend/data/quality_hub.db`，主键是 UUID 字符串 | SQLite，工作项编号是 `<项目key>-<序号>` |
| 鉴权 | 没有鉴权，CORS 全开 | 统一关口 `require_auth`；会话或 API 令牌；项目角色分 manager / developer / tester / viewer，tester 可写 |
| 对外通知 | 没有 | webhook：item.created / item.updated / item.transitioned / item.deleted / comment.created / commit.linked / deployment.created，请求头带 HMAC-SHA256 签名 `X-PM-Signature` |
| 线上 | https://quality-hub.todonot.com/（Mac Mini，Jenkins） | http://192.168.3.9:18930，docker 网络 `fleet_default` 内地址 `http://fleet-pm:8930` |

## 二、数据互通清单

原则：一类数据只有一个数据源，另一边只存引用（对方的 ID 或编号），不存两份。

| 数据 | 数据源 | 另一边存什么 | 方向 | 走哪个接口 |
|---|---|---|---|---|
| 项目对应关系 | 项目管理 | quality-hub 的 project 存项目管理的 `pm_project_key`（需新增字段） | 项目管理 → quality-hub | 读：`GET /api/projects`、`GET /api/projects/{key}` |
| 需求 ↔ 功能点 | 项目管理（需求） | feature 存 `pm_item_key`，如 `FLEET-12`。现有的 `source` 字段语义就是「来源」，可以直接放这个编号，不用加字段 | 项目管理 → quality-hub | 读：`GET /api/projects/{key}/items?kind=requirement`；增量：webhook `item.created` / `item.updated` |
| 测试用例 | quality-hub | 项目管理不存用例，只在需求的评论或链接附件里给一条到 quality-hub 的链接 | quality-hub → 项目管理（只给链接） | `POST /api/items/{key}/links` |
| 执行结果（run） | quality-hub | 需求进入「测试」以后，每次 run 结束在需求下写一条评论：通过 / 失败 / 跳过的条数、通过率、run 链接 | quality-hub → 项目管理 | `POST /api/items/{key}/comments` |
| 失败用例 → 缺陷 | quality-hub 发现，缺陷本身归项目管理 | run_result 存 `pm_bug_key`（需新增字段）；缺陷描述里带用例标题、错误信息、截图链接、run 链接 | quality-hub → 项目管理 | `POST /api/projects/{key}/items`，`kind=bug`、`severity` 由用例优先级映射 |
| 缺陷修好 → 回归 | 项目管理 | quality-hub 收到缺陷进入「测试」以后，对关联用例自动重跑或提示重跑 | 项目管理 → quality-hub | webhook `item.transitioned`（`to=testing`），quality-hub 调现有的 `POST /runs/{run_id}/retry/{result_id}` |
| 提交 | 项目管理 | quality-hub 不存 | 无 | 提交说明里写工作项编号，项目管理用 `POST /api/projects/{key}/commits/scan` 自动关联 |
| 部署 | 项目管理 | quality-hub 收到部署事件后，按项目跑一次冒烟 run | 项目管理 → quality-hub | webhook `deployment.created` |
| 卡口 | 项目管理 | 无 | quality-hub → 项目管理 | 需求「测试 → 合入」、缺陷「测试 → 部署」这两步，quality-hub 只提供依据（评论里的通过率），推进照旧由人或负责人在项目管理里点；不由 quality-hub 自动推进 |

优先级和严重程度映射：用例 `high` → 缺陷 `major`，`medium` → `normal`，`low` → `minor`；`critical` 只由人来定。

## 三、接口怎么接

1. **quality-hub 调项目管理**（写评论、建缺陷、加链接、读需求）
   - 在项目管理里给 quality-hub 开一个机器人账号（is_bot=1），在对应项目里设成 `tester` 角色。tester 能写评论、建缺陷，不能改项目设置，权限刚好够用。
   - 令牌放在 quality-hub 部署时的环境变量（如 `PM_TOKEN`、`PM_BASE`），走 Jenkins 凭据，不写进代码和 `.env.example` 的默认值。
   - 所有调用收在 quality-hub 后端一个新模块里（如 `backend/app/integrations/pm.py`），路由层不直接拼请求。
2. **项目管理通知 quality-hub**（需求变化、缺陷进入测试、部署）
   - 在项目管理的项目上配一个 webhook，订阅 `item.created,item.updated,item.transitioned,deployment.created`，地址指向 quality-hub 新增的 `POST /api/integrations/pm/webhook`。
   - quality-hub 校验 `X-PM-Signature`（HMAC-SHA256），签名不对返回 401。这是 quality-hub 唯一要做的入站鉴权，只收在这一个入口。
   - 项目管理那边已有投递记录和失败重试（`webhook_deliveries`），quality-hub 不用自己轮询补状态。
3. **AI 工人**：已经有 pm-mcp（pm_create_item、pm_comment、pm_link_commit、pm_add_deployment 等工具），AI 走 pm-mcp，不直接调 quality-hub 和项目管理之间的联动接口。

## 四、测试人员在两边怎么用

| 场景 | 在哪里做 | 做什么 |
|---|---|---|
| 领需求 | 项目管理 | 在需求列表里看哪些进了「测试」，或者被设成参与人 |
| 写用例 | quality-hub | 在对应功能点下写用例和脚本。功能点上显示需求编号（如 FLEET-12），点开跳回项目管理 |
| 执行 | quality-hub | 跑 run，看截图和日志，人工覆盖结果 |
| 报结果 | 自动 | run 结束后，quality-hub 在需求下写一条结果评论 |
| 提缺陷 | quality-hub | 在失败结果上点「提缺陷」，自动在项目管理建 bug，带用例、错误、截图；结果行上显示缺陷编号 |
| 跟缺陷 | 项目管理 | 开发修复，关联提交和部署，缺陷推进到「测试」 |
| 回归 | quality-hub | 收到缺陷进入「测试」以后，对应用例标上「待回归」，测试人员点重跑；通过后由测试人员在项目管理里把缺陷推进到「部署 / 验证」 |
| 看质量 | quality-hub | 覆盖率、通过率、趋势看板照旧；项目管理的 bug-fix、backlog 报表看缺陷的修复情况 |

结论：测试人员日常主要用 quality-hub；需求和缺陷的状态只在项目管理里改，两边不重复维护。

## 五、要改的地方（以后实施时参考）

| 模块 | 改动 | 大小 |
|---|---|---|
| quality-hub 后端 | 新增 `integrations/pm.py`（出站客户端）和 webhook 入口；projects 表加 `pm_project_key`，run_results 表加 `pm_bug_key`；run 结束时调用评论接口 | 中，约 3～4 个文件 |
| quality-hub 前端 | 功能点显示需求编号和跳转；结果行加「提缺陷」按钮，显示缺陷编号和「待回归」标记 | 小到中，约 3 个视图 |
| 项目管理 | 不用改代码：机器人账号、tester 角色、webhook 都是现成功能，只需要配置 | 只配置 |
| 部署 | quality-hub 的 Jenkinsfile 注入 `PM_BASE`、`PM_TOKEN`、`PM_WEBHOOK_SECRET` | 小 |

## 六、待定（要人定）

1. quality-hub 现在没有任何鉴权，CORS 全开。接上项目管理以后，它手里会有一个能写项目管理的令牌。上线前是否要先给 quality-hub 加登录？
2. quality-hub 的「项目」是否改成完全跟项目管理的项目一一对应（只能从项目管理导入，不能自己建）？
3. 失败用例是自动建缺陷，还是只给按钮由测试人员确认后再建？本文按「按钮加确认」写，避免一次失败批量刷出缺陷。
4. 部署后的冒烟 run 跑哪些用例：用例上加「冒烟」标记，还是按功能点选？
5. quality-hub 在 Mac Mini 上，项目管理也在 Mac Mini 的 `fleet_default` 网络里。quality-hub 是否加入同一个 docker 网络，直接用 `http://fleet-pm:8930`？