<template>
  <div class="execution-view">
    <!-- 操作栏 -->
    <div class="toolbar">
      <a-space>
        <a-select v-model:value="selectedProjectId" placeholder="选择项目" style="width: 200px" allowClear @change="fetchExecutions">
          <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
        </a-select>
        <a-button type="primary" @click="triggerExecution" :loading="triggering">触发执行</a-button>
      </a-space>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && executions.length === 0" description="暂无执行记录" />
      <a-table v-else :dataSource="executions" :columns="columns" rowKey="id" :pagination="{ pageSize: 10 }">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="execStatusColor(record.status)">{{ execStatusText(record.status) }}</a-tag>
          </template>
          <template v-if="column.key === 'result'">
            <span v-if="record.status === 'pending' || record.status === 'running'">-</span>
            <span v-else>{{ record.passedCases }}/{{ record.totalCases }} 通过</span>
          </template>
          <template v-if="column.key === 'action'">
            <a @click="viewDetail(record)">查看详情</a>
          </template>
        </template>
      </a-table>
    </a-spin>

    <!-- 执行详情抽屉 -->
    <a-drawer v-model:open="showDetail" title="执行详情" width="600">
      <a-descriptions :column="2" bordered size="small" v-if="currentExecution">
        <a-descriptions-item label="执行ID">{{ currentExecution.id }}</a-descriptions-item>
        <a-descriptions-item label="触发方式">{{ currentExecution.triggerType === 'manual' ? '手动' : '定时' }}</a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="execStatusColor(currentExecution.status)">{{ execStatusText(currentExecution.status) }}</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="通过率">
          {{ currentExecution.totalCases ? Math.round(currentExecution.passedCases / currentExecution.totalCases * 100) : 0 }}%
        </a-descriptions-item>
        <a-descriptions-item label="开始时间">{{ currentExecution.startedAt }}</a-descriptions-item>
        <a-descriptions-item label="结束时间">{{ currentExecution.finishedAt || '-' }}</a-descriptions-item>
      </a-descriptions>

      <a-divider>用例结果</a-divider>
      <a-spin :spinning="detailLoading">
        <a-table :dataSource="executionResults" :columns="resultColumns" rowKey="id" size="small" :pagination="false">
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
import { defineComponent, ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import type { Execution, ExecutionResult, Project } from '../types'
import api from '../api'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: '触发方式', dataIndex: 'triggerType', key: 'triggerType', width: 100, customRender: ({ text }: { text: string }) => text === 'manual' ? '手动' : '定时' },
  { title: '状态', key: 'status', width: 100 },
  { title: '结果', key: 'result', width: 120 },
  { title: '开始时间', dataIndex: 'startedAt', key: 'startedAt', width: 180 },
  { title: '操作', key: 'action', width: 100 },
]

const resultColumns = [
  { title: '用例', dataIndex: 'testCaseTitle', key: 'testCaseTitle' },
  { title: '状态', key: 'status', width: 80 },
  { title: '耗时(ms)', dataIndex: 'duration', key: 'duration', width: 80 },
  { title: '错误信息', dataIndex: 'errorMessage', key: 'errorMessage', ellipsis: true },
]

function execStatusColor(s: string) {
  const map: Record<string, string> = { pending: 'default', running: 'processing', passed: 'green', failed: 'red', error: 'orange' }
  return map[s] || 'default'
}
function execStatusText(s: string) {
  const map: Record<string, string> = { pending: '等待中', running: '执行中', passed: '通过', failed: '失败', error: '异常' }
  return map[s] || s
}

export default defineComponent({
  name: 'ExecutionView',
  setup() {
    const projects = ref<Project[]>([])
    const executions = ref<Execution[]>([])
    const executionResults = ref<ExecutionResult[]>([])
    const currentExecution = ref<Execution | null>(null)
    const selectedProjectId = ref<number>()
    const loading = ref(false)
    const triggering = ref(false)
    const showDetail = ref(false)
    const detailLoading = ref(false)

    async function fetchProjects() {
      try {
        const { data } = await api.get<Project[]>('/projects')
        projects.value = data
      } catch { /* 拦截器处理 */ }
    }

    async function fetchExecutions() {
      loading.value = true
      try {
        const params: Record<string, unknown> = {}
        if (selectedProjectId.value) params.projectId = selectedProjectId.value
        const { data } = await api.get<Execution[]>('/executions', { params })
        executions.value = data
      } catch { /* 拦截器处理 */ }
      finally { loading.value = false }
    }

    async function triggerExecution() {
      if (!selectedProjectId.value) {
        message.warning('请先选择项目')
        return
      }
      triggering.value = true
      try {
        await api.post('/executions', { projectId: selectedProjectId.value, triggerType: 'manual' })
        message.success('执行已触发')
        fetchExecutions()
      } catch { /* 拦截器处理 */ }
      finally { triggering.value = false }
    }

    async function viewDetail(record: Execution) {
      currentExecution.value = record
      showDetail.value = true
      detailLoading.value = true
      try {
        const { data } = await api.get<ExecutionResult[]>(`/executions/${record.id}/results`)
        executionResults.value = data
      } catch { /* 拦截器处理 */ }
      finally { detailLoading.value = false }
    }

    onMounted(() => { fetchProjects(); fetchExecutions() })

    return { projects, executions, executionResults, currentExecution, selectedProjectId, loading, triggering, showDetail, detailLoading, columns, resultColumns, execStatusColor, execStatusText, fetchExecutions, triggerExecution, viewDetail }
  },
})
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
</style>
