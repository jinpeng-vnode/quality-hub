import { describe, it, expect, afterEach, vi } from 'vitest'
import TestCaseView from '../src/views/TestCaseView.vue'
import { mountView, mockApi, clickButton, flushPromises } from './helpers'

const ROUTE = { routePath: '/projects/:projectId/cases', path: '/projects/7/cases' }

const FEATURES = [{ id: 1, projectId: 7, title: '登录', description: null, source: null, pmItemKey: null, status: 'pending', caseCount: 2, createdAt: '2026-11-01' }]
const base = { featureId: '1', steps: ['打开登录页'], expectedResult: '进入首页', priority: 'high', midsceneScript: 'assert True', timeout: null, createdAt: '2026-11-01', updatedAt: '2026-11-01' }
const CASES = [
  { ...base, id: 'aaaaaaaa-0001', title: '冒烟登录', smoke: true },
  { ...base, id: 'bbbbbbbb-0002', title: '普通登录', smoke: false, priority: 'low' },
]

afterEach(() => { vi.restoreAllMocks(); document.body.innerHTML = '' })

function smokeCheckbox() {
  const label = Array.from(document.body.querySelectorAll('label')).find(l => l.textContent?.includes('项目管理登记部署后自动执行'))
  const input = label?.querySelector<HTMLInputElement>('input[type="checkbox"]')
  if (!input) throw new Error('找不到「冒烟用例」勾选框')
  return input
}

async function fill(selector: string, value: string) {
  const el = document.body.querySelector<HTMLInputElement | HTMLTextAreaElement>(selector)
  if (!el) throw new Error(`找不到输入框 ${selector}`)
  el.value = value
  el.dispatchEvent(new Event('input'))
  await flushPromises()
}

function rowOf(wrapper: any, title: string) {
  const row = wrapper.findAll('tr').find((r: any) => r.text().includes(title))
  if (!row) throw new Error(`找不到用例行「${title}」`)
  return row
}

describe('测试用例页', () => {
  it('冒烟用例显示「冒烟」标签，普通用例不显示', async () => {
    mockApi({ 'GET /features': FEATURES, 'GET /cases': CASES })
    const { wrapper } = await mountView(TestCaseView, ROUTE)
    expect(rowOf(wrapper, '冒烟登录').text()).toContain('冒烟')
    expect(rowOf(wrapper, '普通登录').text()).not.toContain('冒烟')
  })

  it('新建时勾选「冒烟用例」，保存的 payload 带 smoke: true', async () => {
    const calls = mockApi({ 'GET /features': FEATURES, 'GET /cases': [], 'POST /cases': { id: 'new' } })
    const { wrapper } = await mountView(TestCaseView, ROUTE)
    await clickButton('新建用例')
    // 功能点下拉在 jsdom 里不好点，直接写表单值；其余字段走输入框
    ;(wrapper.vm as any).form.featureId = '1'
    await fill('input[placeholder="请输入用例标题"]', '冒烟新建')
    await fill('input[placeholder="输入步骤"]', '打开首页')
    await fill('textarea[placeholder="预期结果"]', '页面正常')
    ;(wrapper.vm as any).form.midsceneScript = 'assert True'
    await flushPromises()
    expect(smokeCheckbox().checked).toBe(false)
    smokeCheckbox().click()
    await flushPromises()
    expect(smokeCheckbox().checked).toBe(true)
    await clickButton('保存')
    const post = calls.find(c => c.method === 'POST' && c.url === '/cases')
    expect(post?.body).toMatchObject({ featureId: '1', title: '冒烟新建', steps: ['打开首页'], smoke: true })
  })

  it('不勾选时保存 smoke: false', async () => {
    const calls = mockApi({ 'GET /features': FEATURES, 'GET /cases': [], 'POST /cases': { id: 'new' } })
    const { wrapper } = await mountView(TestCaseView, ROUTE)
    await clickButton('新建用例')
    Object.assign((wrapper.vm as any).form, { featureId: '1', title: '普通新建', expectedResult: '正常', midsceneScript: 'assert True' })
    await fill('input[placeholder="输入步骤"]', '打开首页')
    await clickButton('保存')
    const post = calls.find(c => c.method === 'POST' && c.url === '/cases')
    expect(post?.body.smoke).toBe(false)
  })

  it('编辑已标冒烟的用例，勾选框回显勾上，保存仍带 smoke: true', async () => {
    const calls = mockApi({ 'GET /features': FEATURES, 'GET /cases': CASES, 'PUT /cases/aaaaaaaa-0001': { ok: true } })
    const { wrapper } = await mountView(TestCaseView, ROUTE)
    await rowOf(wrapper, '冒烟登录').find('button[aria-label="编辑"]').trigger('click')
    await flushPromises()
    expect(smokeCheckbox().checked).toBe(true)
    await clickButton('保存')
    const put = calls.find(c => c.method === 'PUT')
    expect(put).toMatchObject({ url: '/cases/aaaaaaaa-0001', body: expect.objectContaining({ smoke: true }) })
  })

  it('编辑普通用例，勾选框不勾', async () => {
    mockApi({ 'GET /features': FEATURES, 'GET /cases': CASES })
    const { wrapper } = await mountView(TestCaseView, ROUTE)
    await rowOf(wrapper, '普通登录').find('button[aria-label="编辑"]').trigger('click')
    await flushPromises()
    expect(smokeCheckbox().checked).toBe(false)
  })
})
