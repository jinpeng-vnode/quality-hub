<template>
  <div class="feature-view">
    <!-- 筛选栏 -->
    <div class="toolbar">
      <a-space :size="12">
        <a-select v-model:value="filters.status" placeholder="状态筛选" style="width: 140px" allowClear @change="fetchFeatures">
          <a-select-option value="pending">待覆盖</a-select-option>
          <a-select-option value="partial">部分覆盖</a-select-option>
          <a-select-option value="covered">已覆盖</a-select-option>
        </a-select>
      </a-space>
      <a-button type="primary" @click="showModal = true">
        <template #icon><PlusOutlined /></template>
        新建功能点
      </a-button>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && features.length === 0" description="暂无功能点" />
      <a-table v-else :dataSource="features" :columns="columns" rowKey="id" :pagination="{ pageSize: 20 }" size="middle">
        <template #bodyCell="{ column, record, text }">
          <template v-if="column.key === 'id'">
            <a-tooltip :title="text">
              <span class="id-cell" @click="copyId(text)">{{ String(text).substring(0, 8) }}</span>
            </a-tooltip>
          </template>
          <template v-if="column.key === 'status'">
            <a-tag :color="statusColor(record.status)">{{ statusText(record.status) }}</a-tag>
          </template>
          <template v-if="column.key === 'action'">
            <a-space :size="8">
              <a-button type="link" size="small" @click="editFeature(record)" aria-label="编辑">
                <template #icon><EditOutlined /></template>
              </a-button>
              <a-popconfirm title="确定删除？" @confirm="deleteFeature(record.id)">
                <a-button type="link" size="small" danger aria-label="删除">
                  <template #icon><DeleteOutlined /></template>
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-spin>

    <!-- 新建/编辑弹窗 -->
    <a-modal v-model:open="showModal" :title="editingFeature ? '编辑功能点' : '新建功能点'" @ok="handleSubmit" @cancel="resetForm">
      <a-form :model="form" layout="vertical">
        <a-form-item label="功能点标题" required>
          <a-input v-model:value="form.title" placeholder="请输入功能点标题" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="3" />
        </a-form-item>
        <a-form-item label="来源">
          <a-select v-model:value="form.source" placeholder="选择来源" allowClear>
            <a-select-option value="prd">PRD</a-select-option>
            <a-select-option value="issue">Issue</a-select-option>
            <a-select-option value="manual">手动</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, reactive, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import type { Feature } from '../types'
import api from '../api'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 100, fixed: 'left' as const },
  { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
  { title: '来源', dataIndex: 'source', key: 'source', width: 100 },
  { title: '状态', key: 'status', dataIndex: 'status', width: 100 },
  { title: '用例数', dataIndex: 'caseCount', key: 'caseCount', width: 80 },
  { title: '操作', key: 'action', width: 120, fixed: 'right' as const },
]

function statusColor(s: string) {
  return s === 'covered' ? 'success' : s === 'partial' ? 'processing' : 'warning'
}
function statusText(s: string) {
  return s === 'covered' ? '已覆盖' : s === 'partial' ? '部分覆盖' : '待覆盖'
}

export default defineComponent({
  name: 'FeatureView',
  components: { PlusOutlined, EditOutlined, DeleteOutlined },
  setup() {
    const route = useRoute()
    const projectId = computed(() => route.params.projectId as string)

    const features = ref<Feature[]>([])
    const loading = ref(false)
    const showModal = ref(false)
    const editingFeature = ref<Feature | null>(null)
    const filters = reactive({ status: undefined as string | undefined })
    const form = reactive({ title: '', description: '', source: undefined as string | undefined })

    function copyId(id: string) {
      navigator.clipboard.writeText(id)
      message.success('已复制')
    }

    async function fetchFeatures() {
      loading.value = true
      try {
        const params: Record<string, unknown> = { projectId: projectId.value }
        if (filters.status) params.status = filters.status
        const { data } = await api.get<Feature[]>('/features', { params })
        features.value = data
      } catch { /* 拦截器处理 */ }
      finally { loading.value = false }
    }

    function editFeature(record: Feature) {
      editingFeature.value = record
      form.title = record.title
      form.description = record.description || ''
      form.source = record.source || undefined
      showModal.value = true
    }

    function resetForm() {
      editingFeature.value = null
      form.title = ''
      form.description = ''
      form.source = undefined
    }

    async function handleSubmit() {
      if (!form.title.trim()) {
        message.warning('请填写功能点标题')
        return
      }
      try {
        if (editingFeature.value) {
          await api.put(`/features/${editingFeature.value.id}`, { title: form.title, description: form.description })
          message.success('更新成功')
        } else {
          await api.post('/features', { projectId: projectId.value, title: form.title, description: form.description, source: form.source })
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

    onMounted(fetchFeatures)

    return { features, loading, showModal, editingFeature, filters, form, columns, statusColor, statusText, copyId, editFeature, resetForm, handleSubmit, deleteFeature, fetchFeatures }
  },
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
