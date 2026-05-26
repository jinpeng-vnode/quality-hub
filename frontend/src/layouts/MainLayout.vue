<template>
  <a-layout class="app-layout">
    <a-layout-sider :width="200" :style="{ position: 'fixed', height: '100vh', left: 0 }">
      <div class="logo">QHub</div>
      <a-menu theme="dark" mode="inline" :selectedKeys="selectedKeys" @click="onMenuClick">
        <a-menu-item key="projects">
          <ProjectOutlined />
          <span>项目管理</span>
        </a-menu-item>
        <template v-if="projectId">
          <a-menu-item key="features">
            <AppstoreOutlined />
            <span>功能点管理</span>
          </a-menu-item>
          <a-menu-item key="cases">
            <FileTextOutlined />
            <span>测试用例</span>
          </a-menu-item>
          <a-menu-item key="runs">
            <PlayCircleOutlined />
            <span>执行管理</span>
          </a-menu-item>
          <a-menu-item key="report">
            <BarChartOutlined />
            <span>报告看板</span>
          </a-menu-item>
        </template>
      </a-menu>
    </a-layout-sider>
    <a-layout :style="{ marginLeft: '200px' }">
      <a-layout-content class="app-content">
        <!-- 页面标题 -->
        <div class="page-header">
          <h1 class="page-title">{{ pageTitle }}</h1>
        </div>
        <!-- 页面内容 -->
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script lang="ts">
import { defineComponent, computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  ProjectOutlined,
  AppstoreOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  BarChartOutlined,
} from '@ant-design/icons-vue'

const titleMap: Record<string, string> = {
  projects: '项目管理',
  features: '功能点管理',
  cases: '测试用例管理',
  runs: '执行管理',
  report: '报告看板',
}

export default defineComponent({
  name: 'MainLayout',
  components: { ProjectOutlined, AppstoreOutlined, FileTextOutlined, PlayCircleOutlined, BarChartOutlined },
  setup() {
    const router = useRouter()
    const route = useRoute()

    const projectId = computed(() => route.params.projectId as string | undefined)

    const selectedKeys = computed(() => {
      const name = route.name as string | undefined
      if (name === 'Projects') return ['projects']
      if (name === 'Features') return ['features']
      if (name === 'Cases') return ['cases']
      if (name === 'Runs') return ['runs']
      if (name === 'Report') return ['report']
      return ['projects']
    })

    const pageTitle = computed(() => {
      const key = selectedKeys.value[0]
      return titleMap[key] || '质量管理平台'
    })

    function onMenuClick({ key }: { key: string }) {
      if (key === 'projects') {
        router.push('/projects')
      } else if (projectId.value) {
        router.push(`/projects/${projectId.value}/${key}`)
      }
    }

    return { selectedKeys, pageTitle, projectId, onMenuClick }
  },
})
</script>

<style scoped>
.app-layout { min-height: 100vh; }
.logo { height: 32px; margin: 16px; color: #fff; font-size: 18px; font-weight: bold; text-align: center; line-height: 32px; }
.app-content { padding: 24px; min-width: 960px; }
.page-header { padding-top: 32px; margin-bottom: 24px; }
.page-title { font-size: 20px; font-weight: 600; margin: 0; color: rgba(0, 0, 0, 0.88); }
</style>
