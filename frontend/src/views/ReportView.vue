<template>
  <div class="report-view">
    <!-- 时间范围选择 -->
    <div class="toolbar">
      <span></span>
      <a-select v-model:value="days" style="width: 140px" @change="fetchReport">
        <a-select-option :value="7">最近 7 天</a-select-option>
        <a-select-option :value="14">最近 14 天</a-select-option>
        <a-select-option :value="30">最近 30 天</a-select-option>
      </a-select>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && !dashboard" description="暂无报告数据" />

      <template v-if="dashboard">
        <!-- 统计卡片 -->
        <a-row :gutter="16" class="stats-row">
          <a-col :span="6">
            <a-card :bodyStyle="{ padding: '20px' }">
              <a-statistic title="功能点总数" :value="dashboard.coverage.totalFeatures" />
            </a-card>
          </a-col>
          <a-col :span="6">
            <a-card :bodyStyle="{ padding: '20px' }">
              <a-statistic title="已覆盖" :value="dashboard.coverage.coveredFeatures" />
            </a-card>
          </a-col>
          <a-col :span="6">
            <a-card :bodyStyle="{ padding: '20px' }">
              <a-statistic
                title="覆盖率"
                :value="formatPercent(dashboard.coverage.coverageRate * 100)"
                :valueStyle="{ color: dashboard.coverage.coverageRate >= 0.8 ? '#52c41a' : '#ff4d4f' }"
              />
            </a-card>
          </a-col>
          <a-col :span="6">
            <a-card :bodyStyle="{ padding: '20px' }">
              <a-statistic
                title="通过率"
                :value="formatPercent(dashboard.passRate.passRate * 100)"
                :valueStyle="{ color: dashboard.passRate.passRate >= 0.8 ? '#52c41a' : '#ff4d4f' }"
              />
            </a-card>
          </a-col>
        </a-row>

        <!-- 图表区域 -->
        <a-row :gutter="16" style="margin-top: 24px">
          <a-col :span="12">
            <a-card title="通过率趋势">
              <a-empty v-if="dashboard.trend.length === 0" description="暂无执行数据" :style="{ padding: '40px 0' }" />
              <div v-else ref="lineChartRef" style="height: 300px"></div>
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card title="覆盖状态">
              <a-empty v-if="dashboard.coverage.totalFeatures === 0" description="暂无功能点数据" :style="{ padding: '40px 0' }" />
              <div v-else ref="pieChartRef" style="height: 300px"></div>
            </a-card>
          </a-col>
        </a-row>
      </template>
    </a-spin>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useRoute } from 'vue-router'
import type { DashboardData } from '../types'
import api from '../api'
import * as echarts from 'echarts'

// 百分比格式化：单一文本渲染
function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`
}

export default defineComponent({
  name: 'ReportView',
  setup() {
    const route = useRoute()
    const projectId = computed(() => route.params.projectId as string)

    const dashboard = ref<DashboardData | null>(null)
    const days = ref(7)
    const loading = ref(false)

    const pieChartRef = ref<HTMLElement>()
    const lineChartRef = ref<HTMLElement>()
    let pieChart: echarts.ECharts | null = null
    let lineChart: echarts.ECharts | null = null

    async function fetchReport() {
      loading.value = true
      try {
        const { data } = await api.get<DashboardData>('/reports/dashboard', { params: { projectId: projectId.value } })
        dashboard.value = data
        await nextTick()
        renderCharts()
      } catch { /* 拦截器处理 */ }
      finally { loading.value = false }
    }

    function renderCharts() {
      if (!dashboard.value) return

      // 折线图：通过率趋势
      if (lineChartRef.value && dashboard.value.trend.length > 0) {
        lineChart = echarts.init(lineChartRef.value)
        lineChart.setOption({
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: dashboard.value.trend.map(t => t.date) },
          yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
          series: [{ name: '通过率', type: 'line', data: dashboard.value.trend.map(t => (t.passRate * 100).toFixed(1)), smooth: true, itemStyle: { color: '#1677ff' } }],
        })
      }

      // 饼图：覆盖状态
      if (pieChartRef.value && dashboard.value.coverage.totalFeatures > 0) {
        pieChart = echarts.init(pieChartRef.value)
        const covered = dashboard.value.coverage.coveredFeatures
        const uncovered = dashboard.value.coverage.totalFeatures - covered
        pieChart.setOption({
          tooltip: { trigger: 'item' },
          series: [{
            type: 'pie', radius: ['40%', '70%'],
            data: [
              { value: covered, name: '已覆盖', itemStyle: { color: '#52c41a' } },
              { value: uncovered, name: '未覆盖', itemStyle: { color: '#d9d9d9' } },
            ],
          }],
        })
      }
    }

    function handleResize() { pieChart?.resize(); lineChart?.resize() }

    onMounted(() => {
      fetchReport()
      window.addEventListener('resize', handleResize)
    })

    onUnmounted(() => {
      window.removeEventListener('resize', handleResize)
      pieChart?.dispose()
      lineChart?.dispose()
    })

    return { dashboard, days, loading, pieChartRef, lineChartRef, formatPercent, fetchReport }
  },
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.stats-row { margin-bottom: 16px; }
</style>
