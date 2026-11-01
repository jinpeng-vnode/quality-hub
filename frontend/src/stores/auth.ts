import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export interface CurrentUser {
  id: number
  username: string
  displayName: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<CurrentUser | null>(null)
  const checked = ref(false)

  /** 问一次后端当前是谁；没登录返回 null */
  async function fetchMe(): Promise<CurrentUser | null> {
    try {
      const { data } = await api.get<CurrentUser>('/auth/me')
      user.value = data
    } catch {
      user.value = null
    }
    checked.value = true
    return user.value
  }

  async function login(username: string, password: string) {
    const { data } = await api.post<CurrentUser>('/auth/login', { username, password })
    user.value = data
    checked.value = true
  }

  async function logout() {
    try { await api.post('/auth/logout') } finally {
      user.value = null
    }
  }

  return { user, checked, fetchMe, login, logout }
})
