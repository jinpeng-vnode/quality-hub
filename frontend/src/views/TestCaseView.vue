<template>
  <div class="testcase-view">
    <!-- 筛选栏 -->
    <div class="toolbar">
      <a-space :size="12">
        <a-select v-model:value="filters.featureId" placeholder="选择功能点" style="width: 200px" allowClear @change="fetchCases">
          <a-select-option v-for="f in features" :key="f.id" :value="f.id">{{ f.title }}</a-select-option>
        </a-select>
        <a-select v-model:value="filters.caseType" placeholder="类型" style="width: 120px" allowClear @change="fetchCases">
          <a-select-option value="manual">手动</a-select-option>
          <a-select-option value="e2e">E2E</a-select-option>
        </a-select>
      </a-space>
      <a-button type="primary" @click="openCreate">
        <template #icon><PlusOutlined /></template>
        新建用例
      </a-button>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && testCases.length === 0" description="暂无测试用例" />
      <a-table v-else :dataSource="testCases" :columns="columns" rowKey="id" :pagination="{ pageSize: 20 }" size="middle">
        <template #bodyCell="{ column, record, text }">
          <template v-if="column.key === 'id'">
            <a-tooltip :title="text">
              <span class="id-cell" @click="copyId(text)">{{ String(text).substring(0, 8) }}</span>
            </a-tooltip>
          </template>
          <template v-if="column.key === 'priority'">
            <a-tag :color="priorityColor(record.priority)">{{ priorityText(record.priority) }}</a-tag>
          </template>
          <template v-if="column.key === 'caseType'">
            <a-tag :color="typeColor(record.caseType)">{{ typeText(record.caseType) }}</a-tag>
          </template>
          <template v-if="column.key === 'action'">
            <a-space :size="8">
              <a-button type="link" size="small" @click="editCase(record)" aria-label="编辑">
                <template #icon><EditOutlined /></template>
              </a-button>
              <a-popconfirm title="确定删除？" @confirm="deleteCase(record.id)">
                <a-button type="link" size="small" danger aria-label="删除">
                  <template #icon><DeleteOutlined /></template>
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-spin>

    <!-- 新建/编辑抽屉 -->
    <a-drawer v-model:open="showDrawer" :title="editingCase ? '编辑测试用例' : '新建测试用例'" width="640" @close="resetForm">
      <a-form :model="form" layout="vertical">
        <a-form-item label="所属功能点" required>
          <a-select v-model:value="form.featureId" placeholder="选择功能点">
            <a-select-option v-for="f in features" :key="f.id" :value="f.id">{{ f.title }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="用例标题" required>
          <a-input v-model:value="form.title" placeholder="请输入用例标题" />
        </a-form-item>
        <a-form-item label="测试步骤">
          <div v-for="(step, index) in formSteps" :key="index" style="display: flex; align-items: center; margin-bottom: 8px;">
            <span style="margin-right: 8px; color: rgba(0,0,0,0.45);">{{ index + 1 }}.</span>
            <a-input v-model:value="formSteps[index]" placeholder="输入步骤" style="flex: 1;" />
            <a-button type="link" danger size="small" @click="formSteps.splice(index, 1)" :disabled="formSteps.length <= 1" style="margin-left: 4px;">
              <template #icon><DeleteOutlined /></template>
            </a-button>
          </div>
          <a-button type="dashed" block @click="formSteps.push('')">
            <template #icon><PlusOutlined /></template>
            添加步骤
          </a-button>
        </a-form-item>
        <a-form-item label="预期结果">
          <a-textarea v-model:value="form.expectedResult" :rows="2" placeholder="预期结果" />
        </a-form-item>
        <a-form-item label="优先级">
          <a-select v-model:value="form.priority">
            <a-select-option value="high">高</a-select-option>
            <a-select-option value="medium">中</a-select-option>
            <a-select-option value="low">低</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="类型">
          <a-radio-group v-model:value="form.caseType">
            <a-radio-button value="manual">手动测试</a-radio-button>
            <a-radio-button value="e2e">E2E 脚本</a-radio-button>
          </a-radio-group>
        </a-form-item>
        <a-form-item v-if="form.caseType === 'e2e'" label="超时时间（秒）">
          <a-input-number v-model:value="form.timeout" :min="5" :max="300" placeholder="默认60秒" style="width: 200px;" />
          <span style="margin-left: 8px; color: rgba(0,0,0,0.45);">范围 5-300 秒，不填则使用默认值 60 秒</span>
        </a-form-item>
        <a-form-item v-if="form.caseType === 'e2e'" label="Playwright 脚本">
          <a-collapse style="margin-bottom: 12px;">
            <a-collapse-panel key="guide" header="📖 脚本编写指南（点击展开）">
              <div style="font-size: 13px; line-height: 1.8; color: rgba(0,0,0,0.65);">
                <h4 style="margin: 0 0 8px;">运行环境</h4>
                <ul style="padding-left: 20px; margin: 0 0 12px;">
                  <li><b>Python 3.11</b> + <b>Playwright 1.60</b>（同步 API）</li>
                  <li>浏览器：Chromium（headless 模式，容器内运行）</li>
                  <li>超时：默认 60 秒，可在触发执行时自定义</li>
                  <li>每条用例独立进程执行，串行运行</li>
                </ul>
                <h4 style="margin: 0 0 8px;">可用包</h4>
                <ul style="padding-left: 20px; margin: 0 0 12px;">
                  <li><code>playwright</code> — 浏览器自动化</li>
                  <li><code>os</code>, <code>json</code>, <code>re</code>, <code>time</code> — 标准库</li>
                  <li><code>httpx</code> — HTTP 请求</li>
                </ul>
                <h4 style="margin: 0 0 8px;">截图约定</h4>
                <ul style="padding-left: 20px; margin: 0 0 12px;">
                  <li>环境变量 <code>QH_SCREENSHOT_DIR</code> 为截图保存目录（自动注入）</li>
                  <li>将 .png/.jpg 文件保存到该目录，执行后自动上传图床并展示</li>
                  <li>可保存多张截图，按文件名排序展示</li>
                </ul>
                <h4 style="margin: 0 0 8px;">判定规则</h4>
                <ul style="padding-left: 20px; margin: 0 0 12px;">
                  <li>退出码 0 = <b>通过</b>，非 0 = <b>失败</b></li>
                  <li><code>assert</code> 失败会自动退出码非 0</li>
                  <li>stdout + stderr 自动记录为执行日志</li>
                </ul>
                <h4 style="margin: 0 0 8px;">示例脚本</h4>
                <pre style="background: #f5f5f5; padding: 8px; border-radius: 4px; font-size: 12px; overflow-x: auto;">import os
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = os.environ.get("QH_SCREENSHOT_DIR", ".")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # 访问页面
    page.goto("https://www.baidu.com")

    # 断言验证
    assert "百度" in page.title()

    # 截图（自动上传图床展示）
    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "result.png"))

    # 打印日志（会显示在执行详情中）
    print(f"验证通过: {page.title()}")

    browser.close()</pre>
              </div>
            </a-collapse-panel>
          </a-collapse>
          <a-textarea v-model:value="form.midsceneScript" :rows="15"
            placeholder="import os&#10;from playwright.sync_api import sync_playwright&#10;&#10;# 截图保存目录（执行引擎自动注入）&#10;SCREENSHOT_DIR = os.environ.get('QH_SCREENSHOT_DIR', '.')&#10;&#10;with sync_playwright() as p:&#10;    browser = p.chromium.launch(headless=True)&#10;    page = browser.new_page()&#10;&#10;    # 1. 访问目标页面&#10;    page.goto('https://example.com')&#10;&#10;    # 2. 执行测试操作&#10;    assert 'Example' in page.title()&#10;&#10;    # 3. 截图（保存到 QH_SCREENSHOT_DIR 会自动收集）&#10;    page.screenshot(path=os.path.join(SCREENSHOT_DIR, 'result.png'))&#10;&#10;    browser.close()"
            style="font-family: monospace; font-size: 13px;" />
        </a-form-item>
      </a-form>
      <template #footer>
        <div style="display: flex; justify-content: space-between;">
          <a-button v-if="form.caseType === 'e2e' && form.midsceneScript && editingCase" :loading="executing" @click="executeScript" type="dashed">
            <template #icon><PlayCircleOutlined /></template>
            运行脚本
          </a-button>
          <span v-else></span>
          <a-space>
            <a-button @click="showDrawer = false">取消</a-button>
            <a-button type="primary" @click="handleSubmit">保存</a-button>
          </a-space>
        </div>
        <a-modal v-model:open="showResult" title="执行结果" :footer="null" width="640px">
          <a-result :status="execResult.status === 'passed' ? 'success' : execResult.status === 'skipped' ? 'warning' : 'error'" :title="execResult.status === 'passed' ? '通过' : execResult.status === 'skipped' ? '跳过' : '失败'" :sub-title="`耗时: ${execResult.durationMs}ms`" />
          <div v-if="execResult.log" style="margin-top: 12px;">
            <strong>日志：</strong>
            <pre style="background: #f5f5f5; padding: 8px; border-radius: 4px; max-height: 200px; overflow: auto; font-size: 12px; white-space: pre-wrap;">{{ execResult.log }}</pre>
          </div>
          <div v-if="execResult.screenshots && execResult.screenshots.length" style="margin-top: 12px;">
            <strong>截图：</strong>
            <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px;">
              <a-image v-for="s in execResult.screenshots" :key="s" :src="s" :width="280" />
            </div>
          </div>
        </a-modal>
      </template>
    </a-drawer>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, reactive, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined } from '@ant-design/icons-vue'
import type { TestCase, Feature } from '../types'
import api from '../api'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 100, fixed: 'left' as const },
  { title: '用例标题', dataIndex: 'title', key: 'title', ellipsis: true },
  { title: '优先级', key: 'priority', dataIndex: 'priority', width: 100 },
  { title: '类型', key: 'caseType', dataIndex: 'caseType', width: 100 },
  { title: '操作', key: 'action', width: 120, fixed: 'right' as const },
]

function priorityColor(p: string) {
  return p === 'high' ? 'error' : p === 'medium' ? 'processing' : 'default'
}
function priorityText(p: string) {
  return p === 'high' ? '高' : p === 'medium' ? '中' : '低'
}
function typeColor(t: string) {
  return t === 'e2e' ? 'purple' : 'blue'
}
function typeText(t: string) {
  return t === 'e2e' ? 'E2E' : '手动'
}

export default defineComponent({
  name: 'TestCaseView',
  components: { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined },
  setup() {
    const route = useRoute()
    const projectId = computed(() => route.params.projectId as string)

    const testCases = ref<TestCase[]>([])
    const features = ref<Feature[]>([])
    const loading = ref(false)
    const showDrawer = ref(false)
    const editingCase = ref<TestCase | null>(null)
    const filters = reactive({ featureId: undefined as string | undefined, caseType: undefined as string | undefined })
    const form = reactive({
      featureId: undefined as string | undefined,
      title: '',
      expectedResult: '',
      priority: 'medium' as string,
      caseType: 'manual' as string,
      midsceneScript: '',
      timeout: null as number | null,
    })
    const formSteps = ref<string[]>([''])

    function copyId(id: string) {
      navigator.clipboard.writeText(id)
      message.success('已复制')
    }

    async function fetchFeatures() {
      try {
        const { data } = await api.get<Feature[]>('/features', { params: { projectId: projectId.value } })
        features.value = data
      } catch { /* 拦截器处理 */ }
    }

    async function fetchCases() {
      loading.value = true
      try {
        const params: Record<string, unknown> = { projectId: projectId.value }
        if (filters.featureId) params.featureId = filters.featureId
        if (filters.caseType) params.caseType = filters.caseType
        const { data } = await api.get<TestCase[]>('/cases', { params })
        testCases.value = data
      } catch { /* 拦截器处理 */ }
      finally { loading.value = false }
    }

    function openCreate() { resetForm(); showDrawer.value = true }

    function editCase(record: TestCase) {
      editingCase.value = record
      form.featureId = record.featureId
      form.title = record.title
      // 解析 steps：兼容 JSON 数组和旧的纯文本格式
      if (record.steps) {
        try {
          const parsed = JSON.parse(record.steps)
          formSteps.value = Array.isArray(parsed) ? parsed : [record.steps]
        } catch { formSteps.value = [record.steps] }
      } else {
        formSteps.value = ['']
      }
      form.expectedResult = record.expectedResult || ''
      form.priority = record.priority
      form.caseType = record.caseType
      form.midsceneScript = record.midsceneScript || ''
      form.timeout = record.timeout || null
      showDrawer.value = true
    }

    function resetForm() {
      editingCase.value = null
      form.featureId = undefined
      form.title = ''
      formSteps.value = ['']
      form.expectedResult = ''
      form.priority = 'medium'
      form.caseType = 'manual'
      form.midsceneScript = ''
      form.timeout = null
    }

    async function handleSubmit() {
      if (!form.title.trim() || !form.featureId) {
        message.warning('请填写必填项')
        return
      }
      const stepsArray = formSteps.value.filter(s => s.trim())
      const payload = {
        featureId: form.featureId,
        title: form.title,
        steps: stepsArray.length > 0 ? JSON.stringify(stepsArray) : null,
        expectedResult: form.expectedResult || null,
        priority: form.priority,
        caseType: form.caseType,
        midsceneScript: form.caseType === 'e2e' ? (form.midsceneScript || null) : null,
        timeout: form.caseType === 'e2e' ? form.timeout : null,
      }
      try {
        if (editingCase.value) {
          await api.put(`/cases/${editingCase.value.id}`, payload)
          message.success('更新成功')
        } else {
          await api.post('/cases', payload)
          message.success('创建成功')
        }
        showDrawer.value = false
        resetForm()
        fetchCases()
      } catch { /* 拦截器处理 */ }
    }

    async function deleteCase(id: number) {
      try {
        await api.delete(`/cases/${id}`)
        message.success('删除成功')
        fetchCases()
      } catch { /* 拦截器处理 */ }
    }

    onMounted(() => {
      fetchFeatures()
      // 从 URL query 读取 featureId 自动筛选
      const queryFeatureId = route.query.featureId
      if (queryFeatureId) {
        filters.featureId = String(queryFeatureId)
      }
      fetchCases()
    })

    const executing = ref(false)
    const showResult = ref(false)
    const execResult = reactive({ status: '', log: '', durationMs: 0, screenshots: [] as string[] })

    async function executeScript() {
      if (!editingCase.value) return
      executing.value = true
      try {
        const { data } = await api.post(`/cases/${editingCase.value.id}/execute`)
        execResult.status = data.status
        execResult.log = data.log
        execResult.durationMs = data.durationMs
        execResult.screenshots = data.screenshots || []
        showResult.value = true
      } catch { message.error('执行失败') }
      finally { executing.value = false }
    }

    return { testCases, features, loading, showDrawer, editingCase, filters, form, formSteps, columns, priorityColor, priorityText, typeColor, typeText, copyId, openCreate, editCase, resetForm, handleSubmit, deleteCase, fetchCases, executing, showResult, execResult, executeScript }
  },
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
