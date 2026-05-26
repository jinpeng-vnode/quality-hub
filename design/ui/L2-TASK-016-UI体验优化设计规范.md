# L2-TASK-016 UI 体验优化设计规范

---
创建时间：2026-05-26 15:50
最后更新：2026-05-26 15:50
状态：设计中
---

## 一、全局设计规范

### 1.1 间距系统（基于 4px 网格）

| Token | 值 | 用途 |
|-------|-----|------|
| `--spacing-xs` | 4px | 图标与文字间距 |
| `--spacing-sm` | 8px | 按钮组间距、表格单元格内边距 |
| `--spacing-md` | 16px | 卡片内边距、表单项间距 |
| `--spacing-lg` | 24px | 区块间距、页面内容 padding |
| `--spacing-xl` | 32px | 页面顶部 padding |

### 1.2 颜色系统

基于 Ant Design Vue 4 默认主题，扩展语义色：

| 用途 | 变量 | 色值 | 说明 |
|------|------|------|------|
| 主色 | `colorPrimary` | `#1677ff` | antdv 默认蓝 |
| 成功 | `colorSuccess` | `#52c41a` | 通过/正常状态 |
| 警告 | `colorWarning` | `#faad14` | 中等优先级 |
| 错误 | `colorError` | `#ff4d4f` | 失败/高优先级 |
| 文字-主要 | `colorText` | `rgba(0,0,0,0.88)` | 标题、正文 |
| 文字-次要 | `colorTextSecondary` | `rgba(0,0,0,0.65)` | 描述、辅助信息 |
| 文字-禁用 | `colorTextDisabled` | `rgba(0,0,0,0.25)` | 禁用态 |
| 背景-页面 | `colorBgLayout` | `#f5f5f5` | 页面底色 |
| 背景-容器 | `colorBgContainer` | `#ffffff` | 卡片/表格背景 |
| 边框 | `colorBorder` | `#d9d9d9` | 分割线、边框 |

### 1.3 字体规范

| 层级 | 字号 | 行高 | 字重 | 用途 |
|------|------|------|------|------|
| H1 页面标题 | 20px | 28px | 600 | 页面主标题 |
| H2 区块标题 | 16px | 24px | 600 | 卡片标题、区块标题 |
| 正文 | 14px | 22px | 400 | 表格内容、描述文字 |
| 辅助文字 | 12px | 20px | 400 | 时间戳、ID、标签 |

字体族：`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif`

### 1.4 圆角与阴影

| 元素 | 圆角 | 阴影 |
|------|------|------|
| 按钮 | 6px (`borderRadius`) | 无 |
| 卡片 | 8px (`borderRadiusLG`) | `0 1px 2px 0 rgba(0,0,0,0.03), 0 1px 6px -1px rgba(0,0,0,0.02), 0 2px 4px 0 rgba(0,0,0,0.02)` |
| 弹窗/抽屉 | 8px | antdv 默认 |
| 标签 Tag | 4px (`borderRadiusSM`) | 无 |

---

## 二、布局规范

### 2.1 整体布局结构

```
+--------------------------------------------------+
|                   Header (0px，无顶栏)             |
+----------+---------------------------------------+
|          |        Page Header (标题区)            |
|  Sider   |  padding-top: 32px                    |
|  200px   +---------------------------------------+
|  fixed   |        Content Area                   |
|          |  padding: 24px                        |
|          |  min-width: 960px                     |
|          |  max-width: 100% (自适应)              |
+----------+---------------------------------------+
```

### 2.2 具体数值

| 属性 | 值 | 说明 |
|------|-----|------|
| 侧边栏宽度 | 200px | 固定，`<a-layout-sider :width="200">` |
| 内容区 padding | 24px | 四周统一 |
| 内容区 min-width | 960px | 防止内容挤压 |
| 内容区 max-width | 不限制 | 自适应填满剩余空间 |
| 页面标题 margin-bottom | 24px | 标题与内容区间距 |
| 页面标题 padding-top | 32px | **修复标题裁切问题** |

### 2.3 Ant Design Vue 布局组件配置

```vue
<a-layout style="min-height: 100vh">
  <a-layout-sider :width="200" :style="{ position: 'fixed', height: '100vh', left: 0 }">
    <!-- 导航菜单 -->
  </a-layout-sider>
  <a-layout :style="{ marginLeft: '200px' }">
    <a-layout-content :style="{ padding: '24px', minWidth: '960px' }">
      <!-- 页面标题 -->
      <div :style="{ paddingTop: '32px', marginBottom: '24px' }">
        <h1 :style="{ fontSize: '20px', fontWeight: 600, margin: 0 }">页面标题</h1>
      </div>
      <!-- 页面内容 -->
    </a-layout-content>
  </a-layout>
</a-layout>
```

### 2.4 响应式断点

| 断点 | 宽度 | 行为 |
|------|------|------|
| 最小支持 | 1280px | 侧边栏 200px + 内容区 1080px |
| 标准 | 1440px | 侧边栏 200px + 内容区 1240px |
| 宽屏 | 1920px | 侧边栏 200px + 内容区 1720px（内容居中，max-width 可选 1440px） |

---

## 三、表格规范

### 3.1 行高规范

| 元素 | 行高 | antdv 配置 |
|------|------|-----------|
| 表头 | 48px | `size="middle"` + 自定义 `:style` |
| 数据行 | 56px | `size="middle"` |

antdv `<a-table>` 的 `size` 属性：
- `middle`：默认行高约 56px，符合需求
- 表头需通过 CSS 覆盖：

```css
/* 统一表头行高 */
.ant-table-thead > tr > th {
  padding: 12px 16px !important;  /* (48 - 22) / 2 = 13 ≈ 12px */
  height: 48px;
  font-size: 14px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.88);
  background: #fafafa;
}

/* 统一数据行高 */
.ant-table-tbody > tr > td {
  padding: 16px !important;  /* (56 - 22) / 2 = 17 ≈ 16px */
  height: 56px;
  font-size: 14px;
  vertical-align: middle;
}
```

### 3.2 ID 列处理方案

**方案：截断前 8 位 + Tooltip + 点击复制**

| 属性 | 值 |
|------|-----|
| 列宽 | 100px（固定） |
| 显示内容 | UUID 前 8 位，如 `97f82546` |
| 字体 | `font-family: monospace; font-size: 12px; color: rgba(0,0,0,0.45)` |
| 交互 | hover 显示完整 UUID（Tooltip），点击复制到剪贴板 |

组件实现指引：

```vue
<a-table-column title="ID" dataIndex="id" :width="100" fixed="left">
  <template #default="{ text }">
    <a-tooltip :title="text">
      <span
        class="id-cell"
        @click="copyToClipboard(text)"
        :style="{
          fontFamily: 'monospace',
          fontSize: '12px',
          color: 'rgba(0,0,0,0.45)',
          cursor: 'pointer'
        }"
      >
        {{ text.substring(0, 8) }}
      </span>
    </a-tooltip>
  </template>
</a-table-column>
```

### 3.3 列宽分配原则

| 列类型 | 宽度策略 | 参考值 |
|--------|---------|--------|
| ID | 固定 | 100px |
| 名称/标题 | 自适应（flex） | min 150px |
| 状态/优先级 | 固定 | 100px |
| 时间 | 固定 | 180px |
| 操作 | 固定 | 120px（2个图标）/ 160px（3个图标） |
| 描述 | 自适应 | 单行省略，`ellipsis: true` |

antdv 列配置：

```js
// 通用列配置模式
const columns = [
  { title: 'ID', dataIndex: 'id', width: 100, fixed: 'left' },
  { title: '名称', dataIndex: 'name', ellipsis: true },  // 自适应
  { title: '状态', dataIndex: 'status', width: 100 },
  { title: '创建时间', dataIndex: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 120, fixed: 'right' },
]
```

### 3.4 表格空状态

```vue
<a-table :locale="{ emptyText: '暂无数据' }">
  <template #emptyText>
    <a-empty description="暂无数据" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
  </template>
</a-table>
```

---

## 四、按钮与操作规范

### 4.1 操作列图标按钮方案

| 操作 | 图标 | antdv 组件 | aria-label |
|------|------|-----------|------------|
| 编辑 | `EditOutlined` | `<a-button type="link" size="small">` | "编辑" |
| 删除 | `DeleteOutlined` | `<a-popconfirm>` 包裹 `<a-button type="link" danger size="small">` | "删除" |
| 查看详情 | `EyeOutlined` | `<a-button type="link" size="small">` | "查看详情" |
| 执行 | `PlayCircleOutlined` | `<a-button type="link" size="small">` | "执行" |

### 4.2 图标按钮尺寸与间距

| 属性 | 值 |
|------|-----|
| 按钮类型 | `type="link"` + `size="small"` |
| 图标大小 | 16px（antdv 默认） |
| 按钮间距 | 8px（使用 `<a-space :size="8">` 包裹） |
| hover 效果 | antdv link 按钮默认 hover 变色 |
| 删除按钮 | `danger` 属性，红色 `#ff4d4f` |

### 4.3 操作列实现

```vue
<a-table-column title="操作" :width="120" fixed="right">
  <template #default="{ record }">
    <a-space :size="8">
      <a-button type="link" size="small" @click="handleEdit(record)" aria-label="编辑">
        <template #icon><EditOutlined /></template>
      </a-button>
      <a-popconfirm title="确定删除？" @confirm="handleDelete(record.id)">
        <a-button type="link" size="small" danger aria-label="删除">
          <template #icon><DeleteOutlined /></template>
        </a-button>
      </a-popconfirm>
    </a-space>
  </template>
</a-table-column>
```

### 4.4 页面顶部操作栏布局

```
+------------------------------------------------------------------+
| [筛选器1] [筛选器2]                          [+ 新建XXX]          |
+------------------------------------------------------------------+
```

实现：

```vue
<div :style="{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }">
  <!-- 左侧：筛选器 -->
  <a-space :size="12">
    <a-select placeholder="筛选条件1" :style="{ width: '180px' }" />
    <a-select placeholder="筛选条件2" :style="{ width: '180px' }" />
  </a-space>
  <!-- 右侧：操作按钮 -->
  <a-button type="primary">
    <template #icon><PlusOutlined /></template>
    新建
  </a-button>
</div>
```

---

## 五、卡片规范（项目管理页）

### 5.1 卡片尺寸与网格

| 属性 | 值 |
|------|-----|
| 网格系统 | `<a-row :gutter="[16, 16]">` |
| 列配置 | `:xs="24" :sm="12" :md="8" :lg="8" :xl="6"` |
| 卡片最小宽度 | 280px |
| 卡片内边距 | 20px（`bodyStyle: { padding: '20px' }`） |
| 卡片高度 | 自适应，min-height: 160px |

### 5.2 卡片信息层次

```
+------------------------------------------+
|  项目名称（H2, 16px, 600, colorText）      |
|                                          |
|  项目描述文字，最多两行省略...              |
|  (14px, 400, colorTextSecondary)         |
|                                          |
|  📅 最近活跃：2 小时前    📊 用例: 12     |
|  (12px, colorTextSecondary)              |
+------------------------------------------+
```

### 5.3 antdv 卡片组件配置

```vue
<a-col :xs="24" :sm="12" :md="8" :xl="6">
  <a-card hoverable :bodyStyle="{ padding: '20px' }">
    <!-- 标题 -->
    <h3 :style="{ fontSize: '16px', fontWeight: 600, marginBottom: '8px', color: 'rgba(0,0,0,0.88)' }">
      {{ project.name }}
    </h3>
    <!-- 描述 -->
    <p :style="{
      fontSize: '14px',
      color: 'rgba(0,0,0,0.65)',
      marginBottom: '16px',
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      display: '-webkit-box',
      WebkitLineClamp: 2,
      WebkitBoxOrient: 'vertical'
    }">
      {{ project.description }}
    </p>
    <!-- 元信息 -->
    <div :style="{ fontSize: '12px', color: 'rgba(0,0,0,0.45)' }">
      <span>最近活跃：{{ formatRelativeTime(project.updated_at) }}</span>
    </div>
  </a-card>
</a-col>
```

### 5.4 响应式列数

| 屏幕宽度 | 内容区宽度 | 每行卡片数 |
|----------|-----------|-----------|
| 1280px | ~1080px | 3 |
| 1440px | ~1240px | 4 |
| 1920px | ~1720px | 4-5 |

---

## 六、数据展示规范

### 6.1 百分比格式

**问题**：当前百分比被拆分为多个 DOM 元素渲染。

**方案**：统一使用单一文本节点渲染。

```vue
<!-- ❌ 错误：拆分渲染 -->
<span>{{ Math.floor(value) }}</span>
<span>.{{ decimal }}</span>
<span>%</span>

<!-- ✅ 正确：单一文本 -->
<span>{{ formatPercent(value) }}</span>
```

格式化函数：

```ts
// 百分比格式化：保留 1 位小数
function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`
}
```

### 6.2 时间格式

| 场景 | 格式 | 示例 |
|------|------|------|
| 表格列 | `YYYY-MM-DD HH:mm` | 2026-05-26 15:11 |
| 卡片元信息 | 相对时间 | 2 小时前、3 天前 |
| Tooltip 详情 | 完整格式 | 2026-05-26 15:11:29 |

相对时间规则：
- < 1 分钟：`刚刚`
- < 60 分钟：`X 分钟前`
- < 24 小时：`X 小时前`
- < 30 天：`X 天前`
- ≥ 30 天：显示日期 `YYYY-MM-DD`

### 6.3 状态标签颜色

使用 `<a-tag>` 组件：

| 状态/值 | 颜色 | antdv color 属性 |
|---------|------|-----------------|
| 通过/成功/高 | 绿色 | `color="success"` |
| 失败/错误 | 红色 | `color="error"` |
| 进行中/中等 | 蓝色 | `color="processing"` |
| 待处理/低 | 默认 | `color="default"` |
| 跳过/未执行 | 橙色 | `color="warning"` |

### 6.4 优先级标签

| 优先级 | 显示文本 | 颜色 |
|--------|---------|------|
| critical | 紧急 | `color="error"` |
| high | 高 | `color="warning"` |
| medium | 中 | `color="processing"` |
| low | 低 | `color="default"` |

### 6.5 测试用例类型标签

| 类型 | 显示文本 | 颜色 |
|------|---------|------|
| manual | 手动 | `color="default"` |
| automated | 自动 | `color="processing"` |
| e2e | E2E | `color="purple"` |

### 6.6 执行结果展示

```vue
<!-- 通过率带颜色 -->
<span :style="{ color: passRate === 100 ? '#52c41a' : passRate === 0 ? '#ff4d4f' : '#faad14' }">
  {{ passed }}/{{ total }} 通过
</span>
```

---

## 七、统计卡片规范（报告看板页）

### 7.1 统计卡片样式

```
+------------------+  +------------------+  +------------------+  +------------------+
|  总用例数         |  |  通过率           |  |  覆盖率           |  |  最近执行         |
|  ████████████    |  |  ████████████    |  |  ████████████    |  |  ████████████    |
|  47              |  |  100.0%          |  |  85.0%           |  |  2 小时前         |
+------------------+  +------------------+  +------------------+  +------------------+
```

| 属性 | 值 |
|------|-----|
| 网格 | `<a-row :gutter="16">` + `<a-col :span="6">` |
| 卡片背景 | `#ffffff` |
| 卡片边框 | `1px solid #f0f0f0` |
| 卡片内边距 | 20px |
| 标题 | 14px, `rgba(0,0,0,0.45)`, 400 |
| 数值 | 24px, `rgba(0,0,0,0.88)`, 600 |
| 数值颜色 | 通过率 100% 绿色，0% 红色，其他默认 |

### 7.2 antdv Statistic 组件

```vue
<a-col :span="6">
  <a-card :bodyStyle="{ padding: '20px' }">
    <a-statistic
      title="通过率"
      :value="passRate"
      :precision="1"
      suffix="%"
      :valueStyle="{ color: passRate === 100 ? '#52c41a' : '#1677ff' }"
    />
  </a-card>
</a-col>
```

### 7.3 图表空状态

当无数据时，图表区域显示：

```vue
<a-empty
  description="暂无执行数据"
  :image="Empty.PRESENTED_IMAGE_SIMPLE"
  :style="{ padding: '40px 0' }"
/>
```

---

## 八、交互行为规范

### 8.1 表格交互

| 用户操作 | 触发事件 | 页面响应 |
|---------|---------|---------|
| 点击 ID 单元格 | `@click` | 复制完整 UUID 到剪贴板，显示 `message.success('已复制')` |
| hover ID 单元格 | 原生 hover | 显示 Tooltip 展示完整 UUID |
| 点击编辑图标 | `@click` | 打开编辑弹窗/抽屉 |
| 点击删除图标 | `@click` | 显示 Popconfirm 确认 |
| 确认删除 | `@confirm` | 调用删除 API，成功后刷新列表 |
| 切换筛选器 | `@change` | 重新请求列表数据 |

### 8.2 状态覆盖

| 状态 | 表现 |
|------|------|
| 加载中 | `<a-table :loading="true">` / `<a-spin>` 包裹卡片区域 |
| 空数据 | `<a-empty>` 组件，带描述文字和操作引导 |
| 错误 | `<a-result status="error">` 带重试按钮 |
| 正常 | 正常渲染数据 |

---

## 九、Ant Design Vue 4 主题配置

通过 `ConfigProvider` 统一配置：

```vue
<a-config-provider
  :theme="{
    token: {
      colorPrimary: '#1677ff',
      borderRadius: 6,
      fontSize: 14,
    },
    components: {
      Table: {
        headerBg: '#fafafa',
        headerColor: 'rgba(0,0,0,0.88)',
        rowHoverBg: '#f5f5f5',
      },
      Card: {
        paddingLG: 20,
      },
    },
  }"
>
  <App />
</a-config-provider>
```

---

## 十、自检清单

- [x] 四种状态（加载/空/错误/正常）已覆盖（第八节）
- [x] 每个交互写了触发和响应（第八节）
- [x] 组件数据来源明确（各节组件代码中标注）
- [x] 给出具体 CSS 数值、颜色值、组件属性
- [x] 前端开发者可直接开始写代码
- [x] 解决 PRD 中 6 个核心问题：
  - ID 列截断 → 第三节 3.2
  - 标题裁切 → 第二节 2.2（padding-top: 32px）
  - 行高不一致 → 第三节 3.1（48px/56px）
  - 操作按钮拥挤 → 第四节（图标按钮 + 8px 间距）
  - 内容区宽度 → 第二节 2.2（min-width: 960px，自适应）
  - 百分比格式 → 第六节 6.1（单一文本渲染）
