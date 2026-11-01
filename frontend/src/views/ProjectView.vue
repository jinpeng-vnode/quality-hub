<template>
  <div class="project-view">
    <!-- 操作栏 -->
    <div class="toolbar">
      <span></span>
      <a-button type="primary" @click="showModal = true">
        <template #icon><PlusOutlined /></template>
        从项目管理导入
      </a-button>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && projects.length === 0" description="暂无项目" />
      <a-row v-else :gutter="[16, 16]">
        <a-col v-for="p in projects" :key="p.id" :xs="24" :sm="12" :md="8" :xl="6">
          <a-card hoverable :bodyStyle="{ padding: '20px' }" @click="enterProject(p.id)">
            <h3 class="project-title">{{ p.name }}</h3>
            <p class="project-desc">{{ p.description || '暂无描述' }}</p>
            <div class="project-meta">
              <span>{{ formatRelativeTime(p.updatedAt || p.createdAt) }}</span>
              <span v-if="p.pmProjectKey">🔗 {{ p.pmProjectKey }}</span>
              <span v-if="p.repoUrl">📦 {{ p.repoUrl.split('/').pop() }}</span>
            </div>
            <div class="project-actions" @click.stop>
              <a-popconfirm title="确定删除该项目？所有关联数据将被清除" @confirm="deleteProject(p.id)">
                <a-button type="link" size="small" danger aria-label="删除项目">
                  <template #icon><DeleteOutlined /></template>
                </a-button>
              </a-popconfirm>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>

    <!-- 新建/编辑弹窗 -->
    <a-modal v-model:open="showModal" title="从项目管理导入项目" @ok="handleSubmit" @cancel="resetForm">
      <a-form :model="form" layout="vertical">
        <a-form-item label="项目标识" required extra="项目管理里的项目标识，如 FLEET；名称和描述从项目管理带过来">
          <a-input v-model:value="form.pmProjectKey" placeholder="FLEET" />
        </a-form-item>
        <a-form-item label="仓库地址">
          <a-input v-model:value="form.repoUrl" placeholder="GitHub 仓库 URL" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import type { Project, ProjectImport } from '../types'
import api from '../api'

// 相对时间格式化
function formatRelativeTime(dateStr: string): string {
  const now = Date.now()
  const date = new Date(dateStr).getTime()
  const diff = now - date
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} 小时前`
  const days = Math.floor(hours / 24)
  if (days < 30) return `${days} 天前`
  return dateStr.substring(0, 10)
}

export default defineComponent({
  name: 'ProjectView',
  components: { PlusOutlined, DeleteOutlined },
  setup() {
    const router = useRouter()
    const projects = ref<Project[]>([])
    const loading = ref(false)
    const showModal = ref(false)
    const form = reactive({ pmProjectKey: '', repoUrl: '' })

    async function fetchProjects() {
      loading.value = true
      try {
        const { data } = await api.get<Project[]>('/projects')
        projects.value = data
      } catch { /* 拦截器处理 */ }
      finally { loading.value = false }
    }

    function enterProject(id: number) {
      router.push(`/projects/${id}/features`)
    }

    function resetForm() {
      form.pmProjectKey = ''
      form.repoUrl = ''
    }

    async function handleSubmit() {
      const key = form.pmProjectKey.trim().toUpperCase()
      if (!/^[A-Z][A-Z0-9]{1,9}$/.test(key)) {
        message.warning('项目标识应为 2～10 位大写字母或数字，以字母开头')
        return
      }
      const payload: ProjectImport = { pmProjectKey: key, repoUrl: form.repoUrl || undefined }
      try {
        await api.post('/projects/import', payload)
        message.success('导入成功')
        showModal.value = false
        resetForm()
        fetchProjects()
      } catch { /* 拦截器处理 */ }
    }

    onMounted(fetchProjects)

    async function deleteProject(id: number) {
      try {
        await api.delete(`/projects/${id}`)
        message.success('删除成功')
        fetchProjects()
      } catch { /* 拦截器处理 */ }
    }

    return { projects, loading, showModal, form, formatRelativeTime, enterProject, resetForm, handleSubmit, deleteProject }
  },
})
</script>

<style scoped>
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.project-title { font-size: 16px; font-weight: 600; margin-bottom: 8px; color: rgba(0, 0, 0, 0.88); }
.project-desc {
  font-size: 14px; color: rgba(0, 0, 0, 0.65); margin-bottom: 16px;
  overflow: hidden; text-overflow: ellipsis; display: -webkit-box;
  -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.project-meta { font-size: 12px; color: rgba(0, 0, 0, 0.45); display: flex; gap: 12px; }
.project-actions { position: absolute; top: 8px; right: 8px; }
</style>
