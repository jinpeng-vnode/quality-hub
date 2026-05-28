<template>
  <div class="execution-view">
    <!-- 操作栏 -->
    <div class="toolbar">
      <a-space>
        <a-select v-model:value="selectedFeatureIds" mode="multiple" placeholder="按功能点执行（不选则全部）" style="min-width: 280px;" allowClear :options="featureOptions" />
      </a-space>
      <a-button type="primary" :loading="triggering" @click="handleTrigger">
        <template #icon><PlayCircleOutlined /></template>
        触发执行
      </a-button>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && runs.length === 0" description="暂无执行记录" />
      <a-table v-else :dataSource="runs" :columns="columns" rowKey="id" :pagination="{ pageSize: 20 }" size="middle">
        <template #bodyCell="{ column, record, text }">
          <template v-if="column.key === 'id'">
            <span :title="record.id">{{ record.id.slice(0, 8) }}</span>
          </template>
          <template v-if="column.key === 'status'">
            <a-tag :color="statusColor(record.status)">{{ statusText(record.status) }}</a-tag>
          </template>
          <template v-if="column.key === 'result'">
            <span v-if="record.status === 'pending' || record.status === 'running'">-</span>
            <span v-else :style="{ color: record.passed === record.total ? '#52c41a' : record.passed === 0 ? '#ff4d4f' : '#faad14' }">
              {{ record.passed }}/{{ record.total }} 通过
            </span>
          </template>
          <template v-if="column.key === 'createdAt'">
            {{ formatTime(text) }}
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <router-link :to="`/projects/${projectId}/runs/${record.id}`">查看详情</router-link>
              <a-popconfirm v-if="record.status === 'running'" title="确认取消此执行？" @confirm="cancelRun(record.id)">
                <a-button type="link" danger size="small">取消</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-spin>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlayCircleOutlined } from '@ant-design/icons-vue'
import type { TestRun, Feature } from '../types'
import api from '../api'

const columns = [
  { title: 'ID', key: 'id', dataIndex: 'id', width: 90 },
  { title: '状态', key: 'status', dataIndex: 'status', width: 100 },
  { title: '用例总数', dataIndex: 'total', key: 'total', width: 90 },
  { title: '结果', key: 'result', width: 120 },
  { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt', width: 180 },
  { title: '操作', key: 'action', width: 140, fixed: 'right' as const },
]

function statusColor(s: string) {
  const map: Record<string, string> = { pending: 'default', running: 'processing', passed: 'success', failed: 'error', error: 'warning', completed: 'cyan' }
  return map[s] || 'default'
}
function statusText(s: string) {
  const map: Record<string, string> = { pending: '等待中', running: '执行中', passed: '通过', failed: '失败', error: '异常', completed: '已完成' }
  return map[s] || s
}
function formatTime(t: string | null | undefined): string {
  if (!t) return '-'
  const d = new Date(t)
  if (isNaN(d.getTime())) return t
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default defineComponent({
  name: 'ExecutionView',
  components: { PlayCircleOutlined },
  setup() {
    const route = useRoute()
    const projectId = computed(() => route.params.projectId as string)

    const runs = ref<TestRun[]>([])
    const features = ref<Feature[]>([])
    const selectedFeatureIds = ref<string[]>([])
    const loading = ref(false)
    const triggering = ref(false)

    const featureOptions = computed(() => features.value.map(f => ({ label: `${f.title} (${f.caseCount})`, value: f.id })))

    async function fetchFeatures() {
      try {
        const { data } = await api.get<Feature[]>('/features', { params: { projectId: projectId.value } })
        features.value = data
      } catch { /* */ }
    }

    async function fetchRuns() {
      loading.value = true
      try {
        const { data } = await api.get<TestRun[]>('/runs', { params: { projectId: projectId.value } })
        runs.value = data
      } catch { /* */ }
      finally { loading.value = false }
    }

    async function handleTrigger() {
      triggering.value = true
      try {
        const payload: Record<string, unknown> = { projectId: projectId.value }
        if (selectedFeatureIds.value.length > 0) {
          payload.featureIds = selectedFeatureIds.value
        }
        await api.post('/runs', payload)
        message.success('已触发执行')
        fetchRuns()
        startAutoRefresh()
      } catch { /* */ }
      finally { triggering.value = false }
    }

    async function cancelRun(runId: string) {
      try {
        await api.post(`/runs/${runId}/cancel`)
        message.success('已取消执行')
        fetchRuns()
      } catch { /* */ }
    }

    let refreshTimer: ReturnType<typeof setInterval> | null = null
    function startAutoRefresh() {
      stopAutoRefresh()
      refreshTimer = setInterval(async () => {
        await fetchRuns()
        const hasRunning = runs.value.some(r => r.status === 'running')
        if (!hasRunning) stopAutoRefresh()
      }, 2000)
    }
    function stopAutoRefresh() {
      if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null }
    }

    onMounted(() => {
      fetchFeatures()
      fetchRuns().then(() => {
        if (runs.value.some(r => r.status === 'running')) startAutoRefresh()
      })
    })
    onUnmounted(stopAutoRefresh)

    return { runs, loading, triggering, projectId, columns, selectedFeatureIds, featureOptions, statusColor, statusText, formatTime, fetchRuns, handleTrigger, cancelRun }
  },
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
