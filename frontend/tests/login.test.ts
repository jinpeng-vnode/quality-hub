import { describe, it, expect, afterEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { message } from 'ant-design-vue'
import LoginView from '../src/views/LoginView.vue'
import router from '../src/router'
import { useAuthStore } from '../src/stores/auth'
import { mountView, mockApi, clickButton, flushPromises } from './helpers'

afterEach(() => { vi.restoreAllMocks(); document.body.innerHTML = '' })

const ME = { id: 7, username: 'tester', displayName: '测试员' }
const unauthorized = () => Promise.reject({ response: { status: 401, data: { message: '未登录' } } })

async function fill(username: string, password: string) {
  const user = document.body.querySelector<HTMLInputElement>('input[autocomplete="username"]')
  const pass = document.body.querySelector<HTMLInputElement>('input[type="password"]')
  if (!user || !pass) throw new Error('找不到账号或密码输入框')
  user.value = username
  user.dispatchEvent(new Event('input'))
  pass.value = password
  pass.dispatchEvent(new Event('input'))
  await flushPromises()
}

describe('登录页', () => {
  it('账号为空时提示，不发请求', async () => {
    const calls = mockApi({ 'POST /auth/login': ME })
    const warn = vi.spyOn(message, 'warning')
    await mountView(LoginView, { routePath: '/login' })
    await fill('  ', 'secret')
    await clickButton('登录')
    expect(warn).toHaveBeenCalledWith('请填写账号和密码')
    expect(calls.filter(c => c.url === '/auth/login')).toHaveLength(0)
  })

  it('密码为空时提示，不发请求', async () => {
    const calls = mockApi({ 'POST /auth/login': ME })
    const warn = vi.spyOn(message, 'warning')
    await mountView(LoginView, { routePath: '/login' })
    await fill('tester', '')
    await clickButton('登录')
    expect(warn).toHaveBeenCalledWith('请填写账号和密码')
    expect(calls).toHaveLength(0)
  })

  it('登录成功跳到 redirect，账号去掉首尾空格，store 记下当前用户', async () => {
    const calls = mockApi({ 'POST /auth/login': ME })
    const { router: r } = await mountView(LoginView, { routePath: '/login', path: '/login?redirect=/projects/3/runs' })
    await fill(' tester ', 'secret')
    await clickButton('登录')
    expect(calls).toEqual([{ method: 'POST', url: '/auth/login', body: { username: 'tester', password: 'secret' }, params: undefined }])
    expect(r.currentRoute.value.fullPath).toBe('/projects/3/runs')
    const auth = useAuthStore()
    expect(auth.user).toEqual(ME)
    expect(auth.checked).toBe(true)
  })

  it('不带 redirect 时跳 /projects', async () => {
    mockApi({ 'POST /auth/login': ME })
    const { router: r } = await mountView(LoginView, { routePath: '/login' })
    await fill('tester', 'secret')
    await clickButton('登录')
    expect(r.currentRoute.value.fullPath).toBe('/projects')
  })

  it('redirect 不以 / 开头时不认，跳 /projects', async () => {
    mockApi({ 'POST /auth/login': ME })
    const { router: r } = await mountView(LoginView, { routePath: '/login', path: '/login?redirect=https://evil.example/x' })
    await fill('tester', 'secret')
    await clickButton('登录')
    expect(r.currentRoute.value.fullPath).toBe('/projects')
  })

  it('登录失败停在登录页，store 里没有用户', async () => {
    const calls = mockApi({ 'POST /auth/login': unauthorized })
    const { router: r } = await mountView(LoginView, { routePath: '/login', path: '/login?redirect=/projects' })
    await fill('tester', 'wrong')
    await clickButton('登录')
    expect(calls).toHaveLength(1)
    expect(r.currentRoute.value.path).toBe('/login')
    expect(useAuthStore().user).toBeNull()
  })
})

describe('登录守卫（router/index.ts）', () => {
  it('/auth/me 回 401 时跳 /login?redirect=原地址', async () => {
    setActivePinia(createPinia())
    const calls = mockApi({ 'GET /auth/me': unauthorized })
    await router.push('/projects/5/cases?tab=open')
    expect(router.currentRoute.value.name).toBe('Login')
    expect(router.currentRoute.value.query.redirect).toBe('/projects/5/cases?tab=open')
    expect(calls.map(c => `${c.method} ${c.url}`)).toEqual(['GET /auth/me'])
  })

  it('已登录时放行，只问一次 /auth/me', async () => {
    setActivePinia(createPinia())
    const calls = mockApi({ 'GET /auth/me': ME, 'GET /projects': [] })
    await router.push('/projects/9/report')
    expect(router.currentRoute.value.fullPath).toBe('/projects/9/report')
    await router.push('/projects/9/features')
    expect(router.currentRoute.value.fullPath).toBe('/projects/9/features')
    expect(calls.filter(c => c.url === '/auth/me')).toHaveLength(1)
  })

  it('带 meta.public 的路由放行，不问 /auth/me', async () => {
    setActivePinia(createPinia())
    const calls = mockApi({})
    await router.push('/login?redirect=/projects')
    expect(router.currentRoute.value.name).toBe('Login')
    expect(calls).toHaveLength(0)
  })
})
