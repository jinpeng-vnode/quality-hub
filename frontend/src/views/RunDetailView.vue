<template>
  <div class="run-detail-view">
    <a-page-header :title="`执行详情`" @back="goBack">
      <template #extra>
        <a-tag :color="statusColor(run?.status)">{{ statusText(run?.status) }}</a-tag>
      </template>
    </a-page-header>

    <a-spin :spinning="loading">
      <!-- 报告统计卡片 -->
      <a-row :gutter="16" v-if="report" style="margin-bottom: 24px;">
        <a-col :span="6">
          <a-card size="small"><a-statistic title="通过率" :value="report.passRate" suffix="%" :value-style="{ color: report.passRate >= 80 ? '#52c41a' : report.passRate >= 50 ? '#faad14' : '#ff4d4f' }" /></a-card>
        </a-col>
        <a-col :span="6">
          <a-card size="small"><a-statistic title="通过" :value="report.passed" :value-style="{ color: '#52c41a' }" /></a-card>
        </a-col>
        <a-col :span="6">
          <a-card size="small"><a-statistic title="失败" :value="report.failed" :value-style="{ color: '#ff4d4f' }" /></a-card>
        </a-col>
        <a-col :span="6">
          <a-card size="small"><a-statistic title="跳过" :value="report.skipped" :value-style="{ color: '#faad14' }" /></a-card>
        </a-col>
      </a-row>
      <!-- 执行概要 -->
      <a-descriptions :column="{ xs: 2, sm: 3, md: 4 }" bordered size="small" v-if="run" style="margin-bottom: 24px;">
        <a-descriptions-item label="执行模式">
          <a-tag :color="run.mode === 'script' ? 'purple' : 'blue'">{{ run.mode === 'script' ? '脚本' : '手动' }}</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="用例总数">{{ run.total }}</a-descriptions-item>
        <a-descriptions-item label="通过">
          <span style="color: #52c41a; font-weight: 500;">{{ run.passed }}</span>
        </a-descriptions-item>
        <a-descriptions-item label="失败">
          <span style="color: #ff4d4f; font-weight: 500;">{{ run.failed }}</span>
        </a-descriptions-item>
        <a-descriptions-item label="通过率">{{ passRate }}%</a-descriptions-item>
        <a-descriptions-item label="创建时间">{{ formatTime(run.createdAt) }}</a-descriptions-item>
      </a-descriptions>

      <!-- 手动模式引导文案 -->
      <a-alert v-if="run?.mode === 'manual' && hasPending" type="info" show-icon style="margin-bottom: 16px;"
        message="请逐个标记用例执行结果" description="点击下方用例的「通过」或「失败」按钮来记录执行结果" />

      <!-- 用例结果按功能点分组 -->
      <div v-for="group in groupedResults" :key="group.featureTitle" style="margin-bottom: 24px;">
        <h3 style="margin-bottom: 12px; font-size: 15px; font-weight: 500; color: rgba(0,0,0,0.85); border-left: 3px solid #1890ff; padding-left: 8px;">
          {{ group.featureTitle }}
          <span style="color: rgba(0,0,0,0.45); font-size: 13px; margin-left: 8px;">{{ group.items.length }} 条</span>
        </h3>
        <a-table :dataSource="group.items" :columns="resultColumns" rowKey="id" size="middle"
          :pagination="false">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'caseTitle'">
              {{ record.caseTitle || record.caseId }}
            </template>
            <template v-if="column.key === 'status'">
              <a-tag :color="resultStatusColor(record.status)">{{ statusText(record.status) }}</a-tag>
            </template>
            <template v-if="column.key === 'action'">
              <a-space>
                <template v-if="record.status === 'pending' && run?.mode === 'manual'">
                  <a-button type="primary" size="small" @click="markResult(record, 'passed')">
                    <CheckOutlined /> 通过
                  </a-button>
                  <a-button size="small" danger @click="markResult(record, 'failed')">
                    <CloseOutlined /> 失败
                  </a-button>
                </template>
                <a-button v-if="record.status !== 'pending' && run?.mode === 'script'" size="small" @click="retryResult(record)" :loading="record._retrying">
                  <ReloadOutlined /> 重试
                </a-button>
              </a-space>
            </template>
          </template>
          <template #expandedRowRender="{ record }">
            <div v-if="record.log" style="margin-bottom: 12px;">
              <strong>执行日志：</strong>
              <pre style="background: #f5f5f5; padding: 8px; border-radius: 4px; max-height: 200px; overflow: auto; font-size: 12px; white-space: pre-wrap;">{{ record.log }}</pre>
            </div>
            <div v-if="record.screenshots && record.screenshots.length > 0">
              <strong>截图：</strong>
              <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px;">
                <a-image v-for="s in record.screenshots" :key="s" :src="s" :width="320" style="border: 1px solid #d9d9d9; border-radius: 4px;" />
              </div>
            </div>
            <div v-if="!record.log && (!record.screenshots || record.screenshots.length === 0)">
              <span style="color: rgba(0,0,0,0.45);">无日志和截图</span>
            </div>
          </template>
        </a-table>
      </div>
    </a-spin>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { CheckOutlined, CloseOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import type { TestRun, RunResult } from '../types'
import api from '../api'

const resultColumns = [
  { title: '用例', dataIndex: 'caseId', key: 'caseTitle', ellipsis: true },
  { title: '状态', key: 'status', dataIndex: 'status', width: 100 },
  { title: '耗时(ms)', dataIndex: 'durationMs', key: 'durationMs', width: 100 },
  { title: '错误信息', dataIndex: 'errorMessage', key: 'errorMessage', ellipsis: true },
  { title: '操作', key: 'action', width: 200 },
]

function statusColor(s?: string) {
  const map: Record<string, string> = { pending: 'default', running: 'processing', passed: 'success', failed: 'error', error: 'warning', completed: 'cyan' }
  return map[s || ''] || 'default'
}
function resultStatusColor(s: string) {
  const map: Record<string, string> = { pending: 'default', passed: 'success', failed: 'error', skipped: 'warning' }
  return map[s] || 'default'
}
function statusText(s?: string) {
  const map: Record<string, string> = { pending: '等待中', running: '执行中', passed: '通过', failed: '失败', error: '异常', skipped: '跳过', completed: '已完成' }
  return map[s || ''] || s || ''
}
function formatTime(t: string | null | undefined): string {
  if (!t) return '-'
  const d = new Date(t)
  if (isNaN(d.getTime())) return t
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default defineComponent({
  name: 'RunDetailView',
  components: { CheckOutlined, CloseOutlined, ReloadOutlined },
  setup() {
    const route = useRoute()
    const router = useRouter()
    const projectId = computed(() => route.params.projectId as string)
    const runId = computed(() => route.params.runId as string)

    const run = ref<TestRun | null>(null)
    const results = ref<RunResult[]>([])
    const report = ref<{ passed: number; failed: number; skipped: number; passRate: number; groups: any[] } | null>(null)
    const loading = ref(false)

    const hasPending = computed(() => results.value.some(r => r.status === 'pending'))
    const passRate = computed(() => {
      if (!run.value || run.value.total === 0) return '0.0'
      return ((run.value.passed / run.value.total) * 100).toFixed(1)
    })
    const groupedResults = computed(() => {
      const map = new Map<string, RunResult[]>()
      for (const r of results.value) {
        const key = r.featureTitle || '未分类'
        if (!map.has(key)) map.set(key, [])
        map.get(key)!.push(r)
      }
      return Array.from(map.entries()).map(([featureTitle, items]) => ({ featureTitle, items }))
    })

    function goBack() {
      router.push(`/projects/${projectId.value}/runs`)
    }

    async function fetchData() {
      loading.value = true
      try {
        const [runRes, resultsRes, reportRes] = await Promise.all([
          api.get<TestRun>(`/runs/${runId.value}`),
          api.get<RunResult[]>(`/runs/${runId.value}/results`),
          api.get(`/runs/${runId.value}/report`),
        ])
        run.value = runRes.data
        results.value = resultsRes.data
        report.value = reportRes.data
      } catch { /* 拦截器处理 */ }
      finally { loading.value = false }
    }

    async function markResult(record: RunResult, status: 'passed' | 'failed') {
      try {
        await api.put(`/runs/${runId.value}/results/${record.id}`, { status, errorMessage: '', durationMs: 0 })
        message.success(`已标记为${status === 'passed' ? '通过' : '失败'}`)
        fetchData()
      } catch { /* 拦截器处理 */ }
    }

    async function retryResult(record: RunResult) {
      try {
        await api.post(`/runs/${runId.value}/retry/${record.id}`)
        message.info('已触发重新执行')
        // 启动自动刷新
        startAutoRefresh()
      } catch { /* 拦截器处理 */ }
    }

    // 自动刷新：执行中时每 5 秒刷新一次
    let refreshTimer: ReturnType<typeof setInterval> | null = null
    function startAutoRefresh() {
      stopAutoRefresh()
      refreshTimer = setInterval(async () => {
        await fetchData()
        if (run.value && run.value.status !== 'running') {
          stopAutoRefresh()
        }
      }, 2000)
    }
    function stopAutoRefresh() {
      if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null }
    }

    onMounted(() => {
      fetchData().then(() => {
        if (run.value?.status === 'running') startAutoRefresh()
      })
    })

    return { run, results, groupedResults, loading, hasPending, passRate, report, resultColumns, statusColor, resultStatusColor, statusText, formatTime, goBack, markResult, retryResult }
  },
})
</script>

<style scoped>
.run-detail-view { width: 100%; }
</style>
