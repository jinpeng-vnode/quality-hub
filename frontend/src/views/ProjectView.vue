<template>
  <div class="project-view">
    <!-- 操作栏 -->
    <div class="toolbar">
      <a-button type="primary" @click="showModal = true">新建项目</a-button>
    </div>

    <a-spin :spinning="loading">
      <a-empty v-if="!loading && projects.length === 0" description="暂无项目" />
      <a-row v-else :gutter="16">
        <a-col v-for="p in projects" :key="p.id" :xs="24" :sm="12" :lg="8" style="margin-bottom: 16px">
          <a-card hoverable @click="enterProject(p.id)">
            <template #title>{{ p.name }}</template>
            <p>{{ p.description || '暂无描述' }}</p>
            <p v-if="p.repoUrl" style="font-size: 12px; color: #999">{{ p.repoUrl }}</p>
            <p style="font-size: 12px; color: #999">{{ p.createdAt }}</p>
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
import type { Project } from '../types'
import api from '../api'

export default defineComponent({
  name: 'ProjectView',
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

    function editProject(record: Project) {
      editingProject.value = record
      form.name = record.name
      form.repoUrl = record.repoUrl || ''
      form.description = record.description || ''
      showModal.value = true
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

    async function deleteProject(id: number) {
      try {
        await api.delete(`/projects/${id}`)
        message.success('删除成功')
        fetchProjects()
      } catch { /* 拦截器处理 */ }
    }

    onMounted(fetchProjects)

    return { projects, loading, showModal, editingProject, form, enterProject, editProject, resetForm, handleSubmit, deleteProject }
  },
})
</script>

<style scoped>
.toolbar { margin-bottom: 16px; }
</style>
