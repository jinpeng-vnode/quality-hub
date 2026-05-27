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
            {{ formatTime(text) }}
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
          {{ passRate(currentRun) }}%
        </a-descriptions-item>
        <a-descriptions-item label="开始时间">{{ formatTime(currentRun.startedAt) }}</a-descriptions-item>
        <a-descriptions-item label="结束时间">{{ formatTime(currentRun.finishedAt) }}</a-descriptions-item>
      </a-descriptions>

      <a-divider>用例结果</a-divider>
      <a-spin :spinning="detailLoading">
        <a-table :dataSource="runResults" :columns="resultColumns" rowKey="id" size="small" :pagination="false"
          :expandedRowKeys="expandedKeys" @expand="onExpand">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'caseTitle'">
              {{ caseMap[record.caseId] || record.caseId.substring(0, 8) }}
            </template>
            <template v-if="column.key === 'status'">
              <a-tag :color="resultStatusColor(record.status)">{{ statusText(record.status) }}</a-tag>
            </template>
            <template v-if="column.key === 'action'">
              <a-space v-if="record.status === 'pending' && currentRun?.mode === 'manual'">
                <a-button type="link" size="small" style="color: #52c41a" @click="markResult(record, 'passed')">
                  <CheckOutlined /> 通过
                </a-button>
                <a-button type="link" size="small" danger @click="markResult(record, 'failed')">
                  <CloseOutlined /> 失败
                </a-button>
              </a-space>
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
import { PlayCircleOutlined, EyeOutlined, DownOutlined, CheckOutlined, CloseOutlined } from '@ant-design/icons-vue'
import type { TestRun, RunResult, TestCase } from '../types'
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
  { title: '用例', dataIndex: 'caseId', key: 'caseTitle', width: 200 },
  { title: '状态', key: 'status', dataIndex: 'status', width: 80 },
  { title: '耗时(ms)', dataIndex: 'durationMs', key: 'durationMs', width: 80 },
  { title: '错误信息', dataIndex: 'errorMessage', key: 'errorMessage', ellipsis: true },
  { title: '操作', key: 'action', width: 150 },
]

function statusColor(s: string) {
  const map: Record<string, string> = { pending: 'default', running: 'processing', passed: 'success', failed: 'error', error: 'warning', completed: 'cyan' }
  return map[s] || 'default'
}
function resultStatusColor(s: string) {
  const map: Record<string, string> = { pending: 'default', passed: 'success', failed: 'error', skipped: 'warning' }
  return map[s] || 'default'
}
function statusText(s: string) {
  const map: Record<string, string> = { pending: '等待中', running: '执行中', passed: '通过', failed: '失败', error: '异常', skipped: '跳过', completed: '已完成' }
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
  components: { PlayCircleOutlined, EyeOutlined, DownOutlined, CheckOutlined, CloseOutlined },
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
    // 用例ID -> 标题映射
    const caseMap = ref<Record<string, string>>({})

    function copyId(id: string) {
      navigator.clipboard.writeText(id)
      message.success('已复制')
    }

    function onExpand(expanded: boolean, record: RunResultWithLog) {
      expandedKeys.value = expanded ? [record.id as unknown as string] : []
    }

    // 通过率排除 skipped
    function passRate(run: RunWithMode): string {
      const effective = run.total - (run.skipped || 0)
      if (effective <= 0) return '0.0'
      return ((run.passed / effective) * 100).toFixed(1)
    }

    async function fetchCases() {
      try {
        const { data } = await api.get<TestCase[]>('/cases', { params: { projectId: projectId.value } })
        const map: Record<string, string> = {}
        data.forEach(c => { map[c.id as unknown as string] = c.title })
        caseMap.value = map
      } catch { /* 拦截器处理 */ }
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

    async function markResult(record: RunResultWithLog, status: 'passed' | 'failed') {
      if (!currentRun.value) return
      try {
        await api.put(`/runs/${currentRun.value.id}/results/${record.id}`, { status, errorMessage: '', durationMs: 0 })
        message.success(`已标记为${status === 'passed' ? '通过' : '失败'}`)
        // 刷新详情
        viewDetail(currentRun.value)
        fetchRuns()
      } catch { /* 拦截器处理 */ }
    }

    onMounted(() => { fetchCases(); fetchRuns() })

    return { runs, runResults, currentRun, loading, triggering, showDetail, detailLoading, expandedKeys, caseMap, columns, resultColumns, statusColor, resultStatusColor, statusText, formatTime, passRate, copyId, fetchRuns, handleTrigger, viewDetail, onExpand, markResult }
  },
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.log-block pre { background: #f5f5f5; padding: 8px; border-radius: 4px; max-height: 200px; overflow: auto; font-size: 12px; white-space: pre-wrap; }
</style>
