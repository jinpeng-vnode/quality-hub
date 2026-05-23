import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Project } from '../types'
import api from '../api'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const loading = ref(false)
  const currentProject = ref<Project | null>(null)

  async function fetchProjects() {
    loading.value = true
    try {
      const { data } = await api.get<Project[]>('/projects')
      projects.value = data
    } finally {
      loading.value = false
    }
  }

  function setCurrentProject(project: Project | null) {
    currentProject.value = project
  }

  return { projects, loading, currentProject, fetchProjects, setCurrentProject }
})
