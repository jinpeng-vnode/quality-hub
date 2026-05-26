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
            <a-tooltip :title="text">
              <span class="id-cell" @click="copyId(text)">{{ String(text).substring(0, 8) }}</span>
            </a-tooltip>
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
            <a-tooltip :title="text">
              <span>{{ formatTime(text) }}</span>
            </a-tooltip>
          </template>
          <template v-if="column.key === 'action'">
            <a-button type="link" size="small" @click="viewDetail(record)" aria-label="查看详情">
              <template #icon><EyeOutlined /></template>
            </a-button>
          </template>
        </template>
      </a-table>
    </a-spin>

    <!-- 执行详情抽屉 -->
    <a-drawer v-model:open="showDetail" title="执行详情" width="700">
      <a-descriptions :column="2" bordered size="small" v-if="currentRun">
        <a-descriptions-item label="执行ID">
          <a-tooltip :title="currentRun.id">
            <span class="id-cell">{{ String(currentRun.id).substring(0, 8) }}</span>
          </a-tooltip>
        </a-descriptions-item>
        <a-descriptions-item label="模式">
          <a-tag :color="currentRun.mode === 'script' ? 'purple' : 'blue'">{{ currentRun.mode === 'script' ? '脚本' : '手动' }}</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="statusColor(currentRun.status)">{{ statusText(currentRun.status) }}</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="通过率">
          {{ currentRun.total ? ((currentRun.passed / currentRun.total) * 100).toFixed(1) : '0.0' }}%
        </a-descriptions-item>
        <a-descriptions-item label="开始时间">{{ currentRun.startedAt || '-' }}</a-descriptions-item>
        <a-descriptions-item label="结束时间">{{ currentRun.finishedAt || '-' }}</a-descriptions-item>
      </a-descriptions>

      <a-divider>用例结果</a-divider>
      <a-spin :spinning="detailLoading">
        <a-table :dataSource="runResults" :columns="resultColumns" rowKey="id" size="small" :pagination="false"
          :expandedRowKeys="expandedKeys" @expand="onExpand">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <a-tag :color="resultStatusColor(record.status)">{{ statusText(record.status) }}</a-tag>
            </template>
          </template>
          <template #expandedRowRender="{ record }">
            <div v-if="record.log" class="log-block">
              <strong>执行日志：</strong>
              <pre>{{ record.log }}</pre>
            </div>
            <div v-if="record.errorMessage">
              <strong>错误信息：</strong> {{ record.errorMessage }}
            </div>
            <div v-if="!record.log && !record.errorMessage" style="color: #999;">无日志</div>
          </template>
        </a-table>
      </a-spin>
    </a-drawer>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlayCircleOutlined, EyeOutlined, DownOutlined } from '@ant-design/icons-vue'
import type { TestRun, RunResult } from '../types'
import api from '../api'

interface RunWithMode extends TestRun {
  mode: 'manual' | 'script'
  skipped: number
}

interface RunResultWithLog extends RunResult {
  log: string
}

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 100, fixed: 'left' as const },
  { title: '模式', key: 'mode', dataIndex: 'mode', width: 80 },
  { title: '状态', key: 'status', dataIndex: 'status', width: 100 },
  { title: '总数', dataIndex: 'total', key: 'total', width: 60 },
  { title: '结果', key: 'result', width: 120 },
  { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt', width: 180 },
  { title: '操作', key: 'action', width: 80, fixed: 'right' as const },
]

const resultColumns = [
  { title: '用例ID', dataIndex: 'caseId', key: 'caseId', width: 100 },
  { title: '状态', key: 'status', dataIndex: 'status', width: 80 },
  { title: '耗时(ms)', dataIndex: 'durationMs', key: 'durationMs', width: 80 },
  { title: '错误信息', dataIndex: 'errorMessage', key: 'errorMessage', ellipsis: true },
]

function statusColor(s: string) {
  const map: Record<string, string> = { pending: 'default', running: 'processing', passed: 'success', failed: 'error', error: 'warning' }
  return map[s] || 'default'
}
function resultStatusColor(s: string) {
  const map: Record<string, string> = { pending: 'default', passed: 'success', failed: 'error', skipped: 'warning' }
  return map[s] || 'default'
}
function statusText(s: string) {
  const map: Record<string, string> = { pending: '等待中', running: '执行中', passed: '通过', failed: '失败', error: '异常', skipped: '跳过' }
  return map[s] || s
}
function formatTime(t: string | null): string {
  if (!t) return '-'
  return t.replace(/(\d{4}-\d{2}-\d{2})\s(\d{2}:\d{2}):\d{2}.*/, '$1 $2')
}

export default defineComponent({
  name: 'ExecutionView',
  components: { PlayCircleOutlined, EyeOutlined, DownOutlined },
  setup() {
    const route = useRoute()
    const projectId = computed(() => route.params.projectId as string)

    const runs = ref<RunWithMode[]>([])
    const runResults = ref<RunResultWithLog[]>([])
    const currentRun = ref<RunWithMode | null>(null)
    const loading = ref(false)
    const triggering = ref(false)
    const showDetail = ref(false)
    const detailLoading = ref(false)
    const expandedKeys = ref<string[]>([])

    function copyId(id: string) {
      navigator.clipboard.writeText(id)
      message.success('已复制')
    }

    function onExpand(expanded: boolean, record: RunResultWithLog) {
      expandedKeys.value = expanded ? [record.id as unknown as string] : []
    }

    async function fetchRuns() {
      loading.value = true
      try {
        const { data } = await api.get<RunWithMode[]>('/runs', { params: { projectId: projectId.value } })
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

    async function viewDetail(record: RunWithMode) {
      currentRun.value = record
      showDetail.value = true
      detailLoading.value = true
      expandedKeys.value = []
      try {
        const { data } = await api.get<RunResultWithLog[]>(`/runs/${record.id}/results`)
        runResults.value = data
      } catch { /* 拦截器处理 */ }
      finally { detailLoading.value = false }
    }

    onMounted(fetchRuns)

    return { runs, runResults, currentRun, loading, triggering, showDetail, detailLoading, expandedKeys, columns, resultColumns, statusColor, resultStatusColor, statusText, formatTime, copyId, fetchRuns, handleTrigger, viewDetail, onExpand }
  },
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.log-block pre { background: #f5f5f5; padding: 8px; border-radius: 4px; max-height: 200px; overflow: auto; font-size: 12px; white-space: pre-wrap; }
</style>
