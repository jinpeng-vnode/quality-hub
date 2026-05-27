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
          <a-textarea v-model:value="form.steps" :rows="3" placeholder="Markdown 格式步骤" />
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
        <a-form-item v-if="form.caseType === 'e2e'" label="Playwright 脚本">
          <p style="color: rgba(0,0,0,0.45); margin-bottom: 8px;">编写 Python Playwright 自动化测试脚本，执行时将自动运行</p>
          <a-textarea v-model:value="form.midsceneScript" :rows="15"
            placeholder="import asyncio&#10;from playwright.async_api import async_playwright&#10;&#10;async def test_example():&#10;    async with async_playwright() as p:&#10;        browser = await p.chromium.launch()&#10;        page = await browser.new_page()&#10;        await page.goto('http://localhost:3000')&#10;        # 在此编写测试逻辑&#10;        await browser.close()&#10;&#10;asyncio.run(test_example())"
            style="font-family: monospace; font-size: 13px;" />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-space>
          <a-button @click="showDrawer = false">取消</a-button>
          <a-button type="primary" @click="handleSubmit">保存</a-button>
        </a-space>
      </template>
    </a-drawer>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, reactive, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons-vue'
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
  components: { PlusOutlined, EditOutlined, DeleteOutlined },
  setup() {
    const route = useRoute()
    const projectId = computed(() => route.params.projectId as string)

    const testCases = ref<TestCase[]>([])
    const features = ref<Feature[]>([])
    const loading = ref(false)
    const showDrawer = ref(false)
    const editingCase = ref<TestCase | null>(null)
    const filters = reactive({ featureId: undefined as number | undefined, caseType: undefined as string | undefined })
    const form = reactive({
      featureId: undefined as number | undefined,
      title: '',
      steps: '',
      expectedResult: '',
      priority: 'medium' as string,
      caseType: 'manual' as string,
      midsceneScript: '',
    })

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
      form.steps = record.steps || ''
      form.expectedResult = record.expectedResult || ''
      form.priority = record.priority
      form.caseType = record.caseType
      form.midsceneScript = record.midsceneScript || ''
      showDrawer.value = true
    }

    function resetForm() {
      editingCase.value = null
      form.featureId = undefined
      form.title = ''
      form.steps = ''
      form.expectedResult = ''
      form.priority = 'medium'
      form.caseType = 'manual'
      form.midsceneScript = ''
    }

    async function handleSubmit() {
      if (!form.title.trim() || !form.featureId) {
        message.warning('请填写必填项')
        return
      }
      const payload = {
        featureId: form.featureId,
        title: form.title,
        steps: form.steps || null,
        expectedResult: form.expectedResult || null,
        priority: form.priority,
        caseType: form.caseType,
        midsceneScript: form.caseType === 'e2e' ? (form.midsceneScript || null) : null,
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
        filters.featureId = Number(queryFeatureId)
      }
      fetchCases()
    })

    return { testCases, features, loading, showDrawer, editingCase, filters, form, columns, priorityColor, priorityText, typeColor, typeText, copyId, openCreate, editCase, resetForm, handleSubmit, deleteCase, fetchCases }
  },
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
