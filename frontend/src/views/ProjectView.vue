<template>
  <div class="project-view">
    <!-- 操作栏 -->
    <div class="toolbar">
      <span></span>
      <a-button type="primary" @click="showModal = true">
        <template #icon><PlusOutlined /></template>
        新建项目
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
              <span v-if="p.repoUrl">📦 {{ p.repoUrl.split('/').pop() }}</span>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </a-spin>

    <!-- 新建/编辑弹窗 -->
    <a-modal v-model:open="showModal" :title="editingProject ? '编辑项目' : '新建项目'" @ok="handleSubmit" @cancel="resetForm">
      <a-form :model="form" layout="vertical">
        <a-form-item label="项目名称" required>
          <a-input v-model:value="form.name" placeholder="请输入项目名称" />
        </a-form-item>
        <a-form-item label="仓库地址">
          <a-input v-model:value="form.repoUrl" placeholder="GitHub 仓库 URL" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" placeholder="请输入项目描述" :rows="3" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import type { Project } from '../types'
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
  components: { PlusOutlined },
  setup() {
    const router = useRouter()
    const projects = ref<Project[]>([])
    const loading = ref(false)
    const showModal = ref(false)
    const editingProject = ref<Project | null>(null)
    const form = reactive({ name: '', repoUrl: '', description: '' })

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
      editingProject.value = null
      form.name = ''
      form.repoUrl = ''
      form.description = ''
    }

    async function handleSubmit() {
      if (!form.name.trim()) {
        message.warning('请输入项目名称')
        return
      }
      const payload = { name: form.name, repoUrl: form.repoUrl || undefined, description: form.description || undefined }
      try {
        if (editingProject.value) {
          await api.put(`/projects/${editingProject.value.id}`, payload)
          message.success('更新成功')
        } else {
          await api.post('/projects', payload)
          message.success('创建成功')
        }
        showModal.value = false
        resetForm()
        fetchProjects()
      } catch { /* 拦截器处理 */ }
    }

    onMounted(fetchProjects)

    return { projects, loading, showModal, editingProject, form, formatRelativeTime, enterProject, resetForm, handleSubmit }
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
</style>
