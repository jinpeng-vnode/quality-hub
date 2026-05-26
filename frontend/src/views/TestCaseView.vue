<template>
  <div class="testcase-view">
    <!-- 筛选栏 -->
    <div class="toolbar">
      <a-space>
        <a-select v-model:value="filters.featureId" placeholder="选择功能点" style="width: 200px" allowClear @change="fetchCases">
          <a-select-option v-for="f in features" :key="f.id" :value="f.id">{{ f.title }}</a-select-option>
        </a-select>
        <a-select v-model:value="filters.caseType" placeholder="类型" style="width: 120px" allowClear @change="fetchCases">
          <a-select-option value="manual">手动</a-select-option>
          <a-select-option value="e2e">E2E</a-select-option>
        </a-select>
        <a-button type="primary" @click="openCreate">新建用例</a-button>
      </a-space>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && testCases.length === 0" description="暂无测试用例" />
      <a-table v-else :dataSource="testCases" :columns="columns" rowKey="id" :pagination="{ pageSize: 20 }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'priority'">
            <a-tag :color="record.priority === 'high' ? 'red' : record.priority === 'medium' ? 'orange' : 'blue'">{{ record.priority }}</a-tag>
          </template>
          <template v-if="column.key === 'caseType'">
            <a-tag :color="record.caseType === 'e2e' ? 'purple' : 'default'">{{ record.caseType }}</a-tag>
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a @click="editCase(record)">编辑</a>
              <a-popconfirm title="确认删除？" @confirm="deleteCase(record.id)">
                <a style="color: red">删除</a>
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
          <a-select v-model:value="form.caseType">
            <a-select-option value="manual">手动</a-select-option>
            <a-select-option value="e2e">E2E</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="form.caseType === 'e2e'" label="Midscene 脚本路径">
          <a-input v-model:value="form.midsceneScript" placeholder="脚本文件路径" />
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
import type { TestCase, Feature } from '../types'
import api from '../api'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: '用例标题', dataIndex: 'title', key: 'title' },
  { title: '优先级', key: 'priority', width: 80 },
  { title: '类型', key: 'caseType', width: 80 },
  { title: '操作', key: 'action', width: 120 },
]

export default defineComponent({
  name: 'TestCaseView',
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

    onMounted(() => { fetchFeatures(); fetchCases() })

    return { testCases, features, loading, showDrawer, editingCase, filters, form, columns, openCreate, editCase, resetForm, handleSubmit, deleteCase, fetchCases }
  },
})
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
</style>
