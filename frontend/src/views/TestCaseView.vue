<template>
  <div class="testcase-view">
    <!-- 筛选栏 -->
    <div class="toolbar">
      <a-space>
        <a-select v-model:value="filters.featureId" placeholder="选择功能点" style="width: 200px" allowClear @change="fetchTestCases">
          <a-select-option v-for="f in features" :key="f.id" :value="f.id">{{ f.name }}</a-select-option>
        </a-select>
        <a-select v-model:value="filters.status" placeholder="状态" style="width: 120px" allowClear @change="fetchTestCases">
          <a-select-option value="draft">草稿</a-select-option>
          <a-select-option value="ready">就绪</a-select-option>
          <a-select-option value="obsolete">废弃</a-select-option>
        </a-select>
        <a-button type="primary" @click="openCreate">新建用例</a-button>
      </a-space>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && testCases.length === 0" description="暂无测试用例" />
      <a-table v-else :dataSource="testCases" :columns="columns" rowKey="id" :pagination="{ pageSize: 10 }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'ready' ? 'green' : record.status === 'draft' ? 'blue' : 'default'">
              {{ record.status === 'ready' ? '就绪' : record.status === 'draft' ? '草稿' : '废弃' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'priority'">
            <a-tag :color="record.priority === 'P0' ? 'red' : record.priority === 'P1' ? 'orange' : 'blue'">{{ record.priority }}</a-tag>
          </template>
          <template v-if="column.key === 'steps'">
            {{ record.steps?.length || 0 }} 步
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a @click="editTestCase(record)">编辑</a>
              <a-popconfirm title="确认删除？" @confirm="deleteTestCase(record.id)">
                <a style="color: red">删除</a>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-spin>

    <!-- 新建/编辑抽屉 -->
    <a-drawer
      v-model:open="showDrawer"
      :title="editingCase ? '编辑测试用例' : '新建测试用例'"
      width="640"
      @close="resetForm"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="所属功能点" required>
          <a-select v-model:value="form.featureId" placeholder="选择功能点">
            <a-select-option v-for="f in features" :key="f.id" :value="f.id">{{ f.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="用例标题" required>
          <a-input v-model:value="form.title" placeholder="请输入用例标题" />
        </a-form-item>
        <a-form-item label="前置条件">
          <a-textarea v-model:value="form.precondition" :rows="2" />
        </a-form-item>
        <a-form-item label="优先级">
          <a-select v-model:value="form.priority">
            <a-select-option value="P0">P0</a-select-option>
            <a-select-option value="P1">P1</a-select-option>
            <a-select-option value="P2">P2</a-select-option>
            <a-select-option value="P3">P3</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="状态">
          <a-select v-model:value="form.status">
            <a-select-option value="draft">草稿</a-select-option>
            <a-select-option value="ready">就绪</a-select-option>
            <a-select-option value="obsolete">废弃</a-select-option>
          </a-select>
        </a-form-item>

        <!-- 步骤编辑 -->
        <a-form-item label="测试步骤">
          <div v-for="(step, idx) in form.steps" :key="idx" class="step-row">
            <a-space direction="vertical" style="width: 100%">
              <a-input v-model:value="step.action" :placeholder="`步骤 ${idx + 1}: 操作`" />
              <a-input v-model:value="step.expected" :placeholder="`步骤 ${idx + 1}: 预期结果`" />
            </a-space>
            <a-button type="text" danger @click="removeStep(idx)">删除</a-button>
          </div>
          <a-button type="dashed" block @click="addStep">+ 添加步骤</a-button>
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
import { defineComponent, ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import type { TestCase, Feature } from '../types'
import api from '../api'

interface StepForm { action: string; expected: string }

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: '用例标题', dataIndex: 'title', key: 'title' },
  { title: '优先级', key: 'priority', width: 80 },
  { title: '步骤数', key: 'steps', width: 80 },
  { title: '状态', key: 'status', width: 80 },
  { title: '操作', key: 'action', width: 120 },
]

export default defineComponent({
  name: 'TestCaseView',
  setup() {
    const testCases = ref<TestCase[]>([])
    const features = ref<Feature[]>([])
    const loading = ref(false)
    const showDrawer = ref(false)
    const editingCase = ref<TestCase | null>(null)
    const filters = reactive({ featureId: undefined as number | undefined, status: undefined as string | undefined })
    const form = reactive({
      featureId: undefined as number | undefined,
      title: '',
      precondition: '',
      priority: 'P1',
      status: 'draft',
      steps: [] as StepForm[],
    })

    async function fetchFeatures() {
      try {
        const { data } = await api.get<Feature[]>('/features')
        features.value = data
      } catch { /* 拦截器处理 */ }
    }

    async function fetchTestCases() {
      loading.value = true
      try {
        const params: Record<string, unknown> = {}
        if (filters.featureId) params.featureId = filters.featureId
        if (filters.status) params.status = filters.status
        const { data } = await api.get<TestCase[]>('/testcases', { params })
        testCases.value = data
      } catch { /* 拦截器处理 */ }
      finally { loading.value = false }
    }

    function openCreate() {
      resetForm()
      showDrawer.value = true
    }

    function editTestCase(record: TestCase) {
      editingCase.value = record
      form.featureId = record.featureId
      form.title = record.title
      form.precondition = record.precondition
      form.priority = record.priority
      form.status = record.status
      form.steps = (record.steps || []).map(s => ({ action: s.action, expected: s.expected }))
      showDrawer.value = true
    }

    function resetForm() {
      editingCase.value = null
      form.featureId = undefined
      form.title = ''
      form.precondition = ''
      form.priority = 'P1'
      form.status = 'draft'
      form.steps = []
    }

    function addStep() {
      form.steps.push({ action: '', expected: '' })
    }

    function removeStep(idx: number) {
      form.steps.splice(idx, 1)
    }

    async function handleSubmit() {
      if (!form.title.trim() || !form.featureId) {
        message.warning('请填写必填项')
        return
      }
      const payload = {
        ...form,
        steps: form.steps.map((s, i) => ({ order: i + 1, action: s.action, expected: s.expected })),
      }
      try {
        if (editingCase.value) {
          await api.put(`/testcases/${editingCase.value.id}`, payload)
          message.success('更新成功')
        } else {
          await api.post('/testcases', payload)
          message.success('创建成功')
        }
        showDrawer.value = false
        resetForm()
        fetchTestCases()
      } catch { /* 拦截器处理 */ }
    }

    async function deleteTestCase(id: number) {
      try {
        await api.delete(`/testcases/${id}`)
        message.success('删除成功')
        fetchTestCases()
      } catch { /* 拦截器处理 */ }
    }

    onMounted(() => { fetchFeatures(); fetchTestCases() })

    return { testCases, features, loading, showDrawer, editingCase, filters, form, columns, openCreate, editTestCase, resetForm, addStep, removeStep, handleSubmit, deleteTestCase, fetchTestCases }
  },
})
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.step-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 8px;
  padding: 8px;
  background: #fafafa;
  border-radius: 4px;
}
</style>
