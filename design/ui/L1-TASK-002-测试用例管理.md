# L1-TASK-002 测试用例管理页面 UI 规格

## 页面信息

| 属性 | 值 |
|------|-----|
| 路由 | `/projects/:projectId/cases` |
| 文件路径 | `src/views/CaseListView.vue` |
| 权限 | 登录用户（V1 无认证） |
| 导航位置 | 左侧菜单第 3 项，图标 `ExperimentOutlined` |

## 页面布局

```
┌─────────────────────────────────────────────────────────┐
│ 面包屑：项目列表 > {项目名} > 测试用例管理                │
├─────────────────────────────────────────────────────────┤
│ 操作栏                                                   │
│ [+ 新增用例]          [功能点▼] [优先级▼] [类型▼] [搜索]  │
├───────────────┬─────────────────────────────────────────┤
│ 左侧功能点树   │ 右侧用例表格                             │
│               │                                         │
│ ▼ 功能点 A    │ ┌────┬──────┬────┬────┬────┬──────┐    │
│ ▼ 功能点 B    │ │ ID │ 标题  │优先级│类型 │脚本  │ 操作  │    │
│ ▼ 功能点 C    │ ├────┼──────┼────┼────┼────┼──────┤    │
│               │ │ ...│ ...  │ ...│ ...│ ...│ ...  │    │
│               │ └────┴──────┴────┴────┴────┴──────┘    │
│               │                                         │
│               │ 分页器                                   │
├───────────────┴─────────────────────────────────────────┤
│ （点击行后）用例详情抽屉                                   │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ Tab: 基本信息 | 测试步骤 | Midscene 脚本 | 执行历史  │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 组件列表

| 组件 | Ant Design 组件 | 数据来源 | 说明 |
|------|-----------------|----------|------|
| 面包屑 | `a-breadcrumb` | 路由参数 + store | — |
| 新增按钮 | `a-button type="primary"` | — | 打开新增用例弹窗 |
| 功能点筛选 | `a-select` | API: GET /api/features?projectId=x | 下拉选择功能点 |
| 优先级筛选 | `a-select` | 本地枚举 | high/medium/low |
| 类型筛选 | `a-select` | 本地枚举 | manual/e2e |
| 搜索框 | `a-input-search` | 本地状态 | 按用例标题搜索 |
| 左侧功能点树 | `a-menu mode="inline"` | API: GET /api/features?projectId=x | 点击节点过滤右侧表格 |
| 用例表格 | `a-table` | API: GET /api/cases?featureId=x | 支持行选择 |
| 优先级标签 | `a-tag` | 行数据 | high=红/medium=橙/low=蓝 |
| 类型标签 | `a-tag` | 行数据 | manual=默认/e2e=紫色 |
| 脚本标识 | `a-tooltip` + 图标 | 行数据 midsceneScript | 有脚本时显示绿色图标 |
| 操作列 | `a-space` + `a-button` | — | 编辑、删除 |
| 详情抽屉 | `a-drawer` | API: GET /api/cases/:id | 宽度 720px |
| 抽屉 Tab | `a-tabs` | — | 基本信息/测试步骤/Midscene 脚本/执行历史 |
| 分页器 | `a-pagination`（表格内置） | 前端分页 | 默认 pageSize=20 |

## 交互行为

| 用户操作 | 触发事件 | 页面响应 |
|----------|----------|----------|
| 点击「新增用例」 | 打开 Modal | 显示新增用例表单 |
| 填写表单并提交 | POST /api/cases | 关闭弹窗，刷新表格 |
| 点击左侧功能点菜单项 | GET /api/cases?featureId=x | 右侧表格过滤为该功能点下的用例 |
| 选择优先级/类型筛选 | 前端过滤 | 表格按条件过滤 |
| 输入搜索关键词 | 前端过滤 | 表格按标题过滤，防抖 300ms |
| 点击用例行 | 打开 Drawer | 右侧滑出详情抽屉，加载用例详情 |
| 在详情抽屉编辑信息 | 本地状态更新 | 修改字段值 |
| 点击详情抽屉「保存」 | PUT /api/cases/:id | 保存修改，成功提示 |
| 点击行「编辑」 | 打开 Modal | 显示编辑表单，回填数据 |
| 点击行「删除」 | `Modal.confirm` | 确认后 DELETE /api/cases/:id，刷新表格 |

## 状态覆盖

| 状态 | 表现 |
|------|------|
| 加载中 | 左侧菜单 `a-spin`，右侧表格 `loading` 属性 |
| 空数据 | 表格内嵌 `a-empty`，描述「暂无测试用例」；左侧无功能点时显示「请先创建功能点」 |
| 错误 | `a-alert type="error"` 显示在表格上方 + 重试按钮 |
| 正常 | 左侧功能点列表 + 右侧表格正常展示 |

## 表单字段（新增/编辑用例）

| 字段 | 类型 | 组件 | 校验规则 | 说明 |
|------|------|------|----------|------|
| title | string | `a-input` | 必填，1-200 字符 | 用例标题 |
| featureId | number | `a-select` | 必填 | 关联功能点 |
| priority | enum | `a-select` | 必填，默认 medium | high/medium/low |
| caseType | enum | `a-radio-group` | 必填，默认 manual | manual/e2e |
| steps | string | `a-textarea` | 可选 | Markdown 格式测试步骤 |
| expectedResult | string | `a-textarea` | 可选 | 预期结果 |
| midsceneScript | string | `a-input` | caseType=e2e 时显示 | E2E 脚本文件路径 |

## 详情抽屉 Tab 说明

| Tab | 内容 | 数据来源 |
|-----|------|----------|
| 基本信息 | 标题、功能点、优先级、类型、创建/更新时间 | CaseResponse |
| 测试步骤 | steps 字段的 Markdown 渲染 + 编辑切换 | CaseResponse.steps |
| Midscene 脚本 | 脚本路径展示、配置编辑 | CaseResponse.midsceneScript |
| 执行历史 | 该用例的历史执行结果列表 | API: GET /api/runs?projectId=x 后前端过滤 |

## 调用的后端 API

| API | 方法 | 触发时机 | 用途 |
|-----|------|----------|------|
| `/api/projects/{id}` | GET | 页面加载 | 获取项目名称（面包屑） |
| `/api/features?projectId={id}` | GET | 页面加载 | 获取功能点列表（左侧菜单+筛选下拉） |
| `/api/cases?featureId={id}` | GET | 点击功能点 | 获取该功能点下的用例列表 |
| `/api/cases/{cid}` | GET | 点击用例行 | 获取用例详情 |
| `/api/cases` | POST | 提交新增表单 | 创建用例（body 含 featureId） |
| `/api/cases/{cid}` | PUT | 详情抽屉/编辑弹窗保存 | 更新用例 |
| `/api/cases/{cid}` | DELETE | 确认删除 | 删除用例 |
