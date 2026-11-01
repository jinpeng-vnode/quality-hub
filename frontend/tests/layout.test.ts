import { describe, it, expect, afterEach, vi } from 'vitest'
import { nextTick } from 'vue'
import MainLayout from '../src/layouts/MainLayout.vue'
import { useAuthStore } from '../src/stores/auth'
import { mountView, mockApi, clickButton, flushPromises } from './helpers'

afterEach(() => { vi.restoreAllMocks(); document.body.innerHTML = '' })

const USER = { id: 1, username: 'tester', displayName: '测试小王' }
// Antd 会在两个汉字的按钮文字中间加空格（「退 出」），比对前去掉空白
const text = (w: { text(): string }) => w.text().replace(/\s/g, '')

describe('主布局', () => {
  it('未登录时不显示用户名和「退出」', async () => {
    mockApi({})
    const { wrapper } = await mountView(MainLayout)
    expect(text(wrapper)).not.toContain('退出')
  })

  it('已登录时显示当前用户的显示名和「退出」', async () => {
    mockApi({})
    const { wrapper } = await mountView(MainLayout)
    useAuthStore().user = USER
    await nextTick()
    expect(text(wrapper)).toContain('测试小王')
    expect(text(wrapper)).toContain('退出')
  })

  it('点「退出」后 POST /auth/logout 并跳到登录页', async () => {
    const calls = mockApi({ 'POST /auth/logout': {} })
    const { router } = await mountView(MainLayout)
    // mountView 的内存路由里没有 Login，补一条和 src/router 同名的登录路由
    router.addRoute({ path: '/login', name: 'Login', component: { template: '<div />' } })
    const auth = useAuthStore()
    auth.user = USER
    await nextTick()
    await clickButton('退出')
    await flushPromises()
    expect(calls.some(c => c.method === 'POST' && c.url === '/auth/logout')).toBe(true)
    expect(router.currentRoute.value.name).toBe('Login')
    expect(auth.user).toBeNull()
  })
})