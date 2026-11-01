import axios from 'axios'
import { message } from 'ant-design-vue'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
  // 后端鉴权关口要求写请求带这个头（防 CSRF）；会话在 HttpOnly Cookie 里，前端不碰
  headers: { 'X-Requested-With': 'qh' },
})

// 响应拦截器：统一错误处理；401 跳登录页
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && !err.config?.url?.startsWith('/auth/')) {
      const here = window.location.pathname + window.location.search
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = `/login?redirect=${encodeURIComponent(here)}`
      }
      return Promise.reject(err)
    }
    const msg = err.response?.data?.message || err.response?.data?.detail || err.message || '请求失败'
    message.error(msg)
    return Promise.reject(err)
  }
)

export default api
