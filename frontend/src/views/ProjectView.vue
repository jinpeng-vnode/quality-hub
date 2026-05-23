<template>
  <div class="project-view">
    <!-- 操作栏 -->
    <div class="toolbar">
      <a-button type="primary" @click="showModal = true">新建项目</a-button>
    </div>

    <!-- 加载状态 -->
    <a-spin :spinning="loading">
      <!-- 空状态 -->
      <a-empty v-if="!loading && projects.length === 0" description="暂无项目" />

      <!-- 项目列表 -->
      <a-table
        v-else
        :dataSource="projects"
        :columns="columns"
        rowKey="id"
        :pagination="{ pageSize: 10 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'active' ? 'green' : 'default'">
              {{ record.status === 'active' ? '活跃' : '已归档' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a @click="editProject(record)">编辑</a>
              <a-popconfirm title="确认删除？" @confirm="deleteProject(record.id)">
                <a style="color: red">删除</a>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-spin>

    <!-- 新建/编辑弹窗 -->
    <a-modal
      v-model:open="showModal"
      :title="editingProject ? '编辑项目' : '新建项目'"
      @ok="handleSubmit"
      @cancel="resetForm"
    >
      <a-form :model="form" layout="vertical">
        <a-form-item label="项目名称" required>
          <a-input v-model:value="form.name" placeholder="请输入项目名称" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" placeholder="请输入项目描述" :rows="3" />
        </a-form-item>
        <a-form-item label="状态">
          <a-select v-model:value="form.status">
            <a-select-option value="active">活跃</a-select-option>
            <a-select-option value="archived">已归档</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, reactive } from 'vue'
import { message } from 'ant-design-vue'
import type { Project } from '../types'
import api from '../api'

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
  { title: '项目名称', dataIndex: 'name', key: 'name' },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '状态', key: 'status', width: 100 },
  { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt', width: 180 },
  { title: '操作', key: 'action', width: 120 },
]

export default defineComponent({
  name: 'ProjectView',
  setup() {
    const projects = ref<Project[]>([])
    const loading = ref(false)
    const showModal = ref(false)
    const editingProject = ref<Project | null>(null)
    const form = reactive({ name: '', description: '', status: 'active' as string })

    async function fetchProjects() {
      loading.value = true
      try {
        const { data } = await api.get<Project[]>('/projects')
        projects.value = data
      } catch {
        // 错误已由拦截器处理
      } finally {
        loading.value = false
      }
    }

    function editProject(record: Project) {
      editingProject.value = record
      form.name = record.name
      form.description = record.description
      form.status = record.status
      showModal.value = true
    }

    function resetForm() {
      editingProject.value = null
      form.name = ''
      form.description = ''
      form.status = 'active'
    }

    async function handleSubmit() {
      if (!form.name.trim()) {
        message.warning('请输入项目名称')
        return
      }
      try {
        if (editingProject.value) {
          await api.put(`/projects/${editingProject.value.id}`, form)
          message.success('更新成功')
        } else {
          await api.post('/projects', form)
          message.success('创建成功')
        }
        showModal.value = false
        resetForm()
        fetchProjects()
      } catch {
        // 错误已由拦截器处理
      }
    }

    async function deleteProject(id: number) {
      try {
        await api.delete(`/projects/${id}`)
        message.success('删除成功')
        fetchProjects()
      } catch {
        // 错误已由拦截器处理
      }
    }

    onMounted(fetchProjects)

    return { projects, loading, showModal, editingProject, form, columns, editProject, resetForm, handleSubmit, deleteProject }
  },
})
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
}
</style>
