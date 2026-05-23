<template>
  <div class="report-view">
    <!-- 项目选择 -->
    <div class="toolbar">
      <a-select v-model:value="selectedProjectId" placeholder="选择项目" style="width: 200px" @change="fetchReport">
        <a-select-option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</a-select-option>
      </a-select>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && !stats" description="请选择项目查看报告" />

      <template v-if="stats">
        <!-- 统计卡片 -->
        <a-row :gutter="16" class="stats-row">
          <a-col :span="6">
            <a-statistic title="功能点覆盖率" :value="stats.coverageRate" suffix="%" :valueStyle="{ color: stats.coverageRate >= 80 ? '#3f8600' : '#cf1322' }" />
          </a-col>
          <a-col :span="6">
            <a-statistic title="用例通过率" :value="stats.passRate" suffix="%" :valueStyle="{ color: stats.passRate >= 80 ? '#3f8600' : '#cf1322' }" />
          </a-col>
          <a-col :span="6">
            <a-statistic title="总用例数" :value="stats.totalCases" />
          </a-col>
          <a-col :span="6">
            <a-statistic title="失败用例" :value="stats.failedCases" :valueStyle="{ color: stats.failedCases > 0 ? '#cf1322' : '#3f8600' }" />
          </a-col>
        </a-row>

        <!-- 图表区域 -->
        <a-row :gutter="16" style="margin-top: 24px">
          <a-col :span="12">
            <a-card title="覆盖率/通过率">
              <div ref="pieChartRef" style="height: 300px"></div>
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card title="趋势图">
              <div ref="lineChartRef" style="height: 300px"></div>
            </a-card>
          </a-col>
        </a-row>
      </template>
    </a-spin>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onUnmounted, nextTick } from 'vue'
import type { Project, ReportStats, TrendPoint } from '../types'
import api from '../api'
import * as echarts from 'echarts'

export default defineComponent({
  name: 'ReportView',
  setup() {
    const projects = ref<Project[]>([])
    const stats = ref<ReportStats | null>(null)
    const trend = ref<TrendPoint[]>([])
    const selectedProjectId = ref<number>()
    const loading = ref(false)

    const pieChartRef = ref<HTMLElement>()
    const lineChartRef = ref<HTMLElement>()
    let pieChart: echarts.ECharts | null = null
    let lineChart: echarts.ECharts | null = null

    async function fetchProjects() {
      try {
        const { data } = await api.get<Project[]>('/projects')
        projects.value = data
      } catch { /* 拦截器处理 */ }
    }

    async function fetchReport() {
      if (!selectedProjectId.value) return
      loading.value = true
      try {
        const [statsRes, trendRes] = await Promise.all([
          api.get<ReportStats>(`/reports/${selectedProjectId.value}/stats`),
          api.get<TrendPoint[]>(`/reports/${selectedProjectId.value}/trend`),
        ])
        stats.value = statsRes.data
        trend.value = trendRes.data
        await nextTick()
        renderCharts()
      } catch { /* 拦截器处理 */ }
      finally { loading.value = false }
    }

    function renderCharts() {
      // 饼图：覆盖率和通过率
      if (pieChartRef.value) {
        pieChart = echarts.init(pieChartRef.value)
        pieChart.setOption({
          tooltip: { trigger: 'item' },
          series: [
            {
              type: 'pie',
              radius: ['40%', '70%'],
              data: [
                { value: stats.value!.passedCases, name: '通过', itemStyle: { color: '#52c41a' } },
                { value: stats.value!.failedCases, name: '失败', itemStyle: { color: '#ff4d4f' } },
                { value: stats.value!.totalCases - stats.value!.passedCases - stats.value!.failedCases, name: '其他', itemStyle: { color: '#d9d9d9' } },
              ],
            },
          ],
        })
      }

      // 折线图：趋势
      if (lineChartRef.value && trend.value.length > 0) {
        lineChart = echarts.init(lineChartRef.value)
        lineChart.setOption({
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: trend.value.map(t => t.date) },
          yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
          legend: { data: ['通过率', '覆盖率'] },
          series: [
            { name: '通过率', type: 'line', data: trend.value.map(t => t.passRate), smooth: true, itemStyle: { color: '#1890ff' } },
            { name: '覆盖率', type: 'line', data: trend.value.map(t => t.coverageRate), smooth: true, itemStyle: { color: '#52c41a' } },
          ],
        })
      }
    }

    function handleResize() {
      pieChart?.resize()
      lineChart?.resize()
    }

    onMounted(() => {
      fetchProjects()
      window.addEventListener('resize', handleResize)
    })

    onUnmounted(() => {
      window.removeEventListener('resize', handleResize)
      pieChart?.dispose()
      lineChart?.dispose()
    })

    return { projects, stats, selectedProjectId, loading, pieChartRef, lineChartRef, fetchReport }
  },
})
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
.stats-row { margin-bottom: 16px; }
</style>
