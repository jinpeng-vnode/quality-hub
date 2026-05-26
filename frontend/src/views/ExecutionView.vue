<template>
  <div class="execution-view">
    <!-- 操作栏 -->
    <div class="toolbar">
      <a-button type="primary" @click="triggerRun" :loading="triggering">触发执行</a-button>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && runs.length === 0" description="暂无执行记录" />
      <a-table v-else :dataSource="runs" :columns="columns" rowKey="id" :pagination="{ pageSize: 20 }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="statusColor(record.status)">{{ statusText(record.status) }}</a-tag>
          </template>
          <template v-if="column.key === 'result'">
            <span v-if="record.status === 'pending' || record.status === 'running'">-</span>
            <span v-else>{{ record.passed }}/{{ record.total }} 通过</span>
          </template>
          <template v-if="column.key === 'action'">
            <a @click="viewDetail(record)">查看详情</a>
          </template>
        </template>
      </a-table>
    </a-spin>

    <!-- 执行详情抽屉 -->
    <a-drawer v-model:open="showDetail" title="执行详情" width="600">
      <a-descriptions :column="2" bordered size="small" v-if="currentRun">
        <a-descriptions-item label="执行ID">{{ currentRun.id }}</a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="statusColor(currentRun.status)">{{ statusText(currentRun.status) }}</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="通过率">
          {{ currentRun.total ? Math.round(currentRun.passed / currentRun.total * 100) : 0 }}%
        </a-descriptions-item>
        <a-descriptions-item label="开始时间">{{ currentRun.startedAt || '-' }}</a-descriptions-item>
        <a-descriptions-item label="结束时间">{{ currentRun.finishedAt || '-' }}</a-descriptions-item>
      </a-descriptions>

      <a-divider>用例结果</a-divider>
      <a-spin :spinning="detailLoading">
        <a-table :dataSource="runResults" :columns="resultColumns" rowKey="id" size="small" :pagination="false">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <a-tag :color="record.status === 'passed' ? 'green' : record.status === 'failed' ? 'red' : 'default'">
                {{ record.status }}
              </a-tag>
            </template>
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
import type { TestRun, RunResult } from '../types'
import api from '../api'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: '状态', key: 'status', width: 100 },
  { title: '总数', dataIndex: 'total', key: 'total', width: 60 },
  { title: '结果', key: 'result', width: 120 },
  { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt', width: 180 },
  { title: '操作', key: 'action', width: 100 },
]

const resultColumns = [
  { title: '用例ID', dataIndex: 'caseId', key: 'caseId', width: 80 },
  { title: '状态', key: 'status', width: 80 },
  { title: '耗时(ms)', dataIndex: 'durationMs', key: 'durationMs', width: 80 },
  { title: '错误信息', dataIndex: 'errorMessage', key: 'errorMessage', ellipsis: true },
]

function statusColor(s: string) {
  const map: Record<string, string> = { pending: 'default', running: 'processing', passed: 'green', failed: 'red', error: 'orange' }
  return map[s] || 'default'
}
function statusText(s: string) {
  const map: Record<string, string> = { pending: '等待中', running: '执行中', passed: '通过', failed: '失败', error: '异常' }
  return map[s] || s
}

export default defineComponent({
  name: 'ExecutionView',
  setup() {
    const route = useRoute()
    const projectId = computed(() => route.params.projectId as string)

    const runs = ref<TestRun[]>([])
    const runResults = ref<RunResult[]>([])
    const currentRun = ref<TestRun | null>(null)
    const loading = ref(false)
    const triggering = ref(false)
    const showDetail = ref(false)
    const detailLoading = ref(false)

    async function fetchRuns() {
      loading.value = true
      try {
        const { data } = await api.get<TestRun[]>('/runs', { params: { projectId: projectId.value } })
        runs.value = data
      } catch { /* 拦截器处理 */ }
      finally { loading.value = false }
    }

    async function triggerRun() {
      triggering.value = true
      try {
        await api.post('/runs', { projectId: projectId.value, caseIds: [] })
        message.success('执行已触发')
        fetchRuns()
      } catch { /* 拦截器处理 */ }
      finally { triggering.value = false }
    }

    async function viewDetail(record: TestRun) {
      currentRun.value = record
      showDetail.value = true
      detailLoading.value = true
      try {
        const { data } = await api.get<RunResult[]>(`/runs/${record.id}/results`)
        runResults.value = data
      } catch { /* 拦截器处理 */ }
      finally { detailLoading.value = false }
    }

    onMounted(fetchRuns)

    return { runs, runResults, currentRun, loading, triggering, showDetail, detailLoading, columns, resultColumns, statusColor, statusText, fetchRuns, triggerRun, viewDetail }
  },
})
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
</style>
