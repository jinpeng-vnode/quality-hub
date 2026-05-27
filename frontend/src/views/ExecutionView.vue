<template>
  <div class="execution-view">
    <!-- 操作栏 -->
    <div class="toolbar">
      <span></span>
      <a-dropdown>
        <template #overlay>
          <a-menu @click="handleTrigger">
            <a-menu-item key="manual">手动模式</a-menu-item>
            <a-menu-item key="script">脚本模式</a-menu-item>
          </a-menu>
        </template>
        <a-button type="primary" :loading="triggering">
          <template #icon><PlayCircleOutlined /></template>
          触发执行
          <DownOutlined />
        </a-button>
      </a-dropdown>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && runs.length === 0" description="暂无执行记录" />
      <a-table v-else :dataSource="runs" :columns="columns" rowKey="id" :pagination="{ pageSize: 20 }" size="middle">
        <template #bodyCell="{ column, record, text }">
          <template v-if="column.key === 'id'">
            <span :title="record.id">{{ record.id.slice(0, 8) }}</span>
          </template>
          <template v-if="column.key === 'mode'">
            <a-tag :color="record.mode === 'script' ? 'purple' : 'blue'">{{ record.mode === 'script' ? '脚本' : '手动' }}</a-tag>
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
import { defineComponent, ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlayCircleOutlined, DownOutlined } from '@ant-design/icons-vue'
import type { TestRun } from '../types'
import api from '../api'

const columns = [
  { title: 'ID', key: 'id', dataIndex: 'id', width: 90 },
  { title: '执行模式', key: 'mode', dataIndex: 'mode', width: 100 },
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
  components: { PlayCircleOutlined, DownOutlined },
  setup() {
    const route = useRoute()
    const projectId = computed(() => route.params.projectId as string)

    const runs = ref<TestRun[]>([])
    const loading = ref(false)
    const triggering = ref(false)

    async function fetchRuns() {
      loading.value = true
      try {
        const { data } = await api.get<TestRun[]>('/runs', { params: { projectId: projectId.value } })
        runs.value = data
      } catch { /* 拦截器处理 */ }
      finally { loading.value = false }
    }

    async function handleTrigger({ key }: { key: string }) {
      triggering.value = true
      try {
        await api.post('/runs', { projectId: projectId.value, caseIds: [], mode: key })
        message.success(`已触发${key === 'script' ? '脚本' : '手动'}执行`)
        fetchRuns()
      } catch { /* 拦截器处理 */ }
      finally { triggering.value = false }
    }

    async function cancelRun(runId: string) {
      try {
        await api.post(`/runs/${runId}/cancel`)
        message.success('已取消执行')
        fetchRuns()
      } catch { /* 拦截器处理 */ }
    }

    onMounted(fetchRuns)

    return { runs, loading, triggering, projectId, columns, statusColor, statusText, formatTime, fetchRuns, handleTrigger, cancelRun }
  },
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
</style>
