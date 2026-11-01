/**
 * 前端测试公共工具：
 * - mockApi(routes)：把 src/api 的 axios 实例换成假的，按「方法 路径」返回数据，并记下调用
 * - mountView(component, { route })：带 Antd、pinia、内存路由挂载页面
 * 用法见 tests/smoke.test.ts。每个页面一个测试文件：tests/<页面名>.test.ts
 */
import { vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createMemoryHistory } from 'vue-router'
import Antd from 'ant-design-vue'
import type { Component } from 'vue'
import api from '../src/api'

export type Handler = (body?: any, params?: any) => any
export interface ApiCall { method: string; url: string; body?: any; params?: any }

/** routes 的键形如 "GET /features"、"POST /projects/import"；值是返回的 data 或函数。没登记的路由抛 404 */
export function mockApi(routes: Record<string, any>) {
  const calls: ApiCall[] = []
  const handle = (method: string) => async (url: string, a?: any, b?: any) => {
    const body = method === 'GET' || method === 'DELETE' ? undefined : a
    const params = method === 'GET' ? a?.params : b?.params
    calls.push({ method, url, body, params })
    const key = `${method} ${url}`
    if (!(key in routes)) {
      return Promise.reject({ response: { status: 404, data: { message: `假接口没有 ${key}` } } })
    }
    const v = routes[key]
    const data = typeof v === 'function' ? await v(body, params) : v
    return { data }
  }
  vi.spyOn(api, 'get').mockImplementation(handle('GET') as any)
  vi.spyOn(api, 'post').mockImplementation(handle('POST') as any)
  vi.spyOn(api, 'put').mockImplementation(handle('PUT') as any)
  vi.spyOn(api, 'delete').mockImplementation(handle('DELETE') as any)
  return calls
}

export async function mountView(component: Component, opts: { path?: string; routePath?: string } = {}) {
  setActivePinia(createPinia())
  const routePath = opts.routePath ?? '/'
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: routePath, component },
      { path: '/:pathMatch(.*)*', component: { template: '<div />' } },
    ],
  })
  await router.push(opts.path ?? routePath)
  await router.isReady()
  const wrapper = mount(component, {
    attachTo: document.body,
    global: { plugins: [Antd, router] },
  })
  await flushPromises()
  return { wrapper, router }
}

/** 页面弹窗、抽屉都挂在 body 上，按文字找按钮并点击 */
export async function clickButton(text: string) {
  const btn = Array.from(document.body.querySelectorAll('button')).find(b => b.textContent?.replace(/\s/g, '').includes(text))
  if (!btn) throw new Error(`找不到按钮「${text}」`)
  btn.click()
  await flushPromises()
}

export { flushPromises }
