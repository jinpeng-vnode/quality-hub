import { describe, it, expect, afterEach, vi } from 'vitest'
import NotFoundView from '../src/views/NotFoundView.vue'
import { mountView, mockApi } from './helpers'
import api from '../src/api'

afterEach(() => { vi.restoreAllMocks(); document.body.innerHTML = '' })

describe('测试底座', () => {
  it('能挂载页面', async () => {
    const { wrapper } = await mountView(NotFoundView)
    expect(wrapper.text()).toContain('返回首页')
  })
  it('假 api 记下调用、没登记的路由回 404', async () => {
    const calls = mockApi({ 'GET /ping': { ok: true } })
    expect((await api.get('/ping')).data).toEqual({ ok: true })
    await expect(api.get('/nope')).rejects.toMatchObject({ response: { status: 404 } })
    expect(calls.map(c => c.url)).toEqual(['/ping', '/nope'])
  })
})
