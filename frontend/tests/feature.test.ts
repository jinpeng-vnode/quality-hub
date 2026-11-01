import { describe, it, expect, afterEach, vi } from 'vitest'
import { message } from 'ant-design-vue'
import FeatureView from '../src/views/FeatureView.vue'
import { mountView, mockApi, clickButton, flushPromises } from './helpers'

// 弹窗没配中文 locale，Antd 默认确定按钮文字是 OK
const OK = 'OK'
const ROUTE = { routePath: '/projects/:projectId/features', path: '/projects/7/features' }

const FEATURES = [
  { id: 1, projectId: 7, title: '登录', description: '账号登录', source: null, pmItemKey: 'FLEET-12', status: 'covered', caseCount: 3, createdAt: '2026-11-01' },
  { id: 2, projectId: 7, title: '导出', description: null, source: null, pmItemKey: null, status: 'pending', caseCount: 0, createdAt: '2026-11-01' },
]

afterEach(() => { vi.restoreAllMocks(); document.body.innerHTML = '' })

/** 弹窗里的输入框按 placeholder 找，写入后触发 input 事件让 v-model 生效 */
async function fill(placeholder: string, value: string) {
  const el = document.body.querySelector<HTMLInputElement>(`input[placeholder="${placeholder}"]`)
  if (!el) throw new Error(`找不到输入框「${placeholder}」`)
  el.value = value
  el.dispatchEvent(new Event('input'))
  await flushPromises()
}

function writes(calls: ReturnType<typeof mockApi>) {
  return calls.filter(c => c.method === 'POST' || c.method === 'PUT')
}

describe('功能点页', () => {
  it('列表有「关联需求」列，并显示 pmItemKey', async () => {
    const calls = mockApi({ 'GET /features': FEATURES })
    const { wrapper } = await mountView(FeatureView, ROUTE)
    const headers = wrapper.findAll('th').map(th => th.text())
    expect(headers).toContain('关联需求')
    expect(wrapper.text()).toContain('FLEET-12')
    expect(calls[0]).toMatchObject({ method: 'GET', url: '/features', params: { projectId: '7' } })
  })

  it('新建时需求编号格式不对：提示，不发请求', async () => {
    const calls = mockApi({ 'GET /features': [] })
    const warn = vi.spyOn(message, 'warning')
    await mountView(FeatureView, ROUTE)
    await clickButton('新建功能点')
    await fill('请输入功能点标题', '新功能')
    await fill('FLEET-12', 'fleet12')
    await clickButton(OK)
    expect(warn).toHaveBeenCalledWith('需求编号格式应为 FLEET-12 这样')
    expect(writes(calls)).toHaveLength(0)
  })

  it('新建时小写编号转成大写后提交', async () => {
    const calls = mockApi({ 'GET /features': [], 'POST /features': { id: 3 } })
    await mountView(FeatureView, ROUTE)
    await clickButton('新建功能点')
    await fill('请输入功能点标题', '新功能')
    await fill('FLEET-12', 'fleet-12')
    await clickButton(OK)
    expect(writes(calls)).toEqual([
      expect.objectContaining({ method: 'POST', url: '/features', body: expect.objectContaining({ projectId: '7', title: '新功能', pmItemKey: 'FLEET-12' }) }),
    ])
  })

  it('新建时编号留空，提交 pmItemKey: null', async () => {
    const calls = mockApi({ 'GET /features': [], 'POST /features': { id: 3 } })
    await mountView(FeatureView, ROUTE)
    await clickButton('新建功能点')
    await fill('请输入功能点标题', '新功能')
    await clickButton(OK)
    const [post] = writes(calls)
    expect(post.body.pmItemKey).toBeNull()
  })

  it('编辑时格式不对：提示，不发请求', async () => {
    const calls = mockApi({ 'GET /features': FEATURES })
    const warn = vi.spyOn(message, 'warning')
    const { wrapper } = await mountView(FeatureView, ROUTE)
    await wrapper.findAll('button[aria-label="编辑"]')[0].trigger('click')
    await flushPromises()
    await fill('FLEET-12', 'fleet12')
    await clickButton(OK)
    expect(warn).toHaveBeenCalledWith('需求编号格式应为 FLEET-12 这样')
    expect(writes(calls)).toHaveLength(0)
  })

  it('编辑时回显原编号，改成小写后转大写提交', async () => {
    const calls = mockApi({ 'GET /features': FEATURES, 'PUT /features/1': { ok: true } })
    const { wrapper } = await mountView(FeatureView, ROUTE)
    await wrapper.findAll('button[aria-label="编辑"]')[0].trigger('click')
    await flushPromises()
    const input = document.body.querySelector<HTMLInputElement>('input[placeholder="FLEET-12"]')!
    expect(input.value).toBe('FLEET-12')
    await fill('FLEET-12', 'qh-5')
    await clickButton(OK)
    expect(writes(calls)).toEqual([
      expect.objectContaining({ method: 'PUT', url: '/features/1', body: expect.objectContaining({ pmItemKey: 'QH-5' }) }),
    ])
  })

  it('编辑时清空编号，提交空串表示解除关联', async () => {
    const calls = mockApi({ 'GET /features': FEATURES, 'PUT /features/1': { ok: true } })
    const { wrapper } = await mountView(FeatureView, ROUTE)
    await wrapper.findAll('button[aria-label="编辑"]')[0].trigger('click')
    await flushPromises()
    await fill('FLEET-12', '')
    await clickButton(OK)
    const [put] = writes(calls)
    expect(put).toMatchObject({ method: 'PUT', url: '/features/1' })
    expect(put.body.pmItemKey).toBe('')
  })
})
