<template>
  <div class="feature-view">
    <!-- 筛选栏 -->
    <div class="toolbar">
      <a-space>
        <a-select v-model:value="filters.projectId" placeholder="选择项目" style="width: 200px" allowClear @change="fetchFeatures">
          <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
        </a-select>
        <a-select v-model:value="filters.status" placeholder="状态筛选" style="width: 140px" allowClear @change="fetchFeatures">
          <a-select-option value="pending">待处理</a-select-option>
          <a-select-option value="in_progress">进行中</a-select-option>
          <a-select-option value="done">已完成</a-select-option>
        </a-select>
        <a-button type="primary" @click="showModal = true">新建功能点</a-button>
      </a-space>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && features.length === 0" description="暂无功能点" />
      <a-table v-else :dataSource="features" :columns="columns" rowKey="id" :pagination="{ pageSize: 10 }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="statusColor(record.status)">{{ statusText(record.status) }}</a-tag>
          </template>
          <template v-if="column.key === 'priority'">
            <a-tag :color="priorityColor(record.priority)">{{ record.priority }}</a-tag>
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a @click="editFeature(record)">编辑</a>
              <a-popconfirm title="确认删除？" @confirm="deleteFeature(record.id)">
                <a style="color: red">删除</a>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-spin>

    <!-- 新建/编辑弹窗 -->
    <a-modal v-model:open="showModal" :title="editingFeature ? '编辑功能点' : '新建功能点'" @ok="handleSubmit" @cancel="resetForm">
      <a-form :model="form" layout="vertical">
        <a-form-item label="所属项目" required>
          <a-select v-model:value="form.projectId" placeholder="选择项目">
            <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="功能点名称" required>
          <a-input v-model:value="form.name" placeholder="请输入功能点名称" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="3" />
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
            <a-select-option value="pending">待处理</a-select-option>
            <a-select-option value="in_progress">进行中</a-select-option>
            <a-select-option value="done">已完成</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import type { Feature, Project } from '../types'
import api from '../api'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: '功能点名称', dataIndex: 'name', key: 'name' },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '优先级', key: 'priority', width: 80 },
  { title: '状态', key: 'status', width: 100 },
  { title: '操作', key: 'action', width: 120 },
]

function statusColor(s: string) {
  return s === 'done' ? 'green' : s === 'in_progress' ? 'blue' : 'default'
}
function statusText(s: string) {
  return s === 'done' ? '已完成' : s === 'in_progress' ? '进行中' : '待处理'
}
function priorityColor(p: string) {
  return p === 'P0' ? 'red' : p === 'P1' ? 'orange' : p === 'P2' ? 'blue' : 'default'
}

export default defineComponent({
  name: 'FeatureView',
  setup() {
    const features = ref<Feature[]>([])
    const projects = ref<Project[]>([])
    const loading = ref(false)
    const showModal = ref(false)
    const editingFeature = ref<Feature | null>(null)
    const filters = reactive({ projectId: undefined as number | undefined, status: undefined as string | undefined })
    const form = reactive({ projectId: undefined as number | undefined, name: '', description: '', priority: 'P1', status: 'pending' })

    async function fetchProjects() {
      try {
        const { data } = await api.get<Project[]>('/projects')
        projects.value = data
      } catch { /* 拦截器处理 */ }
    }

    async function fetchFeatures() {
      loading.value = true
      try {
        const params: Record<string, unknown> = {}
        if (filters.projectId) params.projectId = filters.projectId
        if (filters.status) params.status = filters.status
        const { data } = await api.get<Feature[]>('/features', { params })
        features.value = data
      } catch { /* 拦截器处理 */ }
      finally { loading.value = false }
    }

    function editFeature(record: Feature) {
      editingFeature.value = record
      form.projectId = record.projectId
      form.name = record.name
      form.description = record.description
      form.priority = record.priority
      form.status = record.status
      showModal.value = true
    }

    function resetForm() {
      editingFeature.value = null
      form.projectId = undefined
      form.name = ''
      form.description = ''
      form.priority = 'P1'
      form.status = 'pending'
    }

    async function handleSubmit() {
      if (!form.name.trim() || !form.projectId) {
        message.warning('请填写必填项')
        return
      }
      try {
        if (editingFeature.value) {
          await api.put(`/features/${editingFeature.value.id}`, form)
          message.success('更新成功')
        } else {
          await api.post('/features', form)
          message.success('创建成功')
        }
        showModal.value = false
        resetForm()
        fetchFeatures()
      } catch { /* 拦截器处理 */ }
    }

    async function deleteFeature(id: number) {
      try {
        await api.delete(`/features/${id}`)
        message.success('删除成功')
        fetchFeatures()
      } catch { /* 拦截器处理 */ }
    }

    onMounted(() => { fetchProjects(); fetchFeatures() })

    return { features, projects, loading, showModal, editingFeature, filters, form, columns, statusColor, statusText, priorityColor, editFeature, resetForm, handleSubmit, deleteFeature, fetchFeatures }
  },
})
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
</style>
