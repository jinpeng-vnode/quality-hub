import { describe, it, expect, afterEach, vi } from 'vitest'
import RunDetailView from '../src/views/RunDetailView.vue'
import { mountView, mockApi, clickButton, flushPromises } from './helpers'

afterEach(() => { vi.restoreAllMocks(); document.body.innerHTML = '' })

const ROUTE = '/projects/:projectId/runs/:runId'
const PATH = '/projects/7/runs/42'

function result(id: number, over: Record<string, any> = {}) {
  return {
    id, runId: 42, caseId: id, caseTitle: `用例${id}`, featureId: 'f1', featureTitle: '登录',
    status: 'passed', errorMessage: null, durationMs: 10, log: '', screenshots: [],
    pmBugKey: null, regressionPending: false, ...over,
  }
}

const RESULTS = [
  result(1, { status: 'failed' }),
  result(2, { status: 'failed', pmBugKey: 'FLEET-9' }),
  result(3, { status: 'passed', regressionPending: true }),
]

function baseRoutes(extra: Record<string, any> = {}) {
  return {
    'GET /runs/42': { id: 42, projectId: 7, status: 'completed', total: 3, passed: 1, failed: 2, createdAt: '2026-11-01T00:00:00Z' },
    'GET /runs/42/results': RESULTS,
    'GET /runs/42/report': { passed: 1, failed: 2, skipped: 0, passRate: 33, groups: [] },
    ...extra,
  }
}

const buttons = (text: string) =>
  Array.from(document.body.querySelectorAll('button')).filter(b => b.textContent?.replace(/\s/g, '').includes(text))

function modalTitleInput(): HTMLInputElement {
  const input = document.body.querySelector('.ant-modal input') as HTMLInputElement | null
  if (!input) throw new Error('找不到弹窗里的标题输入框')
  return input
}

async function typeInto(input: HTMLInputElement, value: string) {
  input.value = value
  input.dispatchEvent(new Event('input'))
  await flushPromises()
}

describe('执行详情', () => {
  it('只有失败且没提过缺陷的结果显示「提缺陷」；已有缺陷显示编号；待回归显示标签', async () => {
    mockApi(baseRoutes())
    const { wrapper } = await mountView(RunDetailView, { routePath: ROUTE, path: PATH })
    expect(buttons('提缺陷')).toHaveLength(1)
    expect(wrapper.text()).toContain('FLEET-9')
    expect(wrapper.text()).toContain('待回归')
  })

  it('点「提缺陷」先取草稿并回显在确认框里', async () => {
    const calls = mockApi(baseRoutes({
      'GET /runs/42/results/1/bug-draft': { title: '登录失败：用例1', description: '复现步骤', severity: 'normal' },
    }))
    await mountView(RunDetailView, { routePath: ROUTE, path: PATH })
    await clickButton('提缺陷')
    expect(calls.some(c => c.method === 'GET' && c.url === '/runs/42/results/1/bug-draft')).toBe(true)
    expect(document.body.textContent).toContain('确认提缺陷到项目管理')
    expect(modalTitleInput().value).toBe('登录失败：用例1')
    expect(calls.some(c => c.method === 'POST')).toBe(false)
  })

  it('标题清空后确认提交只提示，不发请求', async () => {
    const calls = mockApi(baseRoutes({
      'GET /runs/42/results/1/bug-draft': { title: '登录失败：用例1', description: '', severity: 'normal' },
    }))
    await mountView(RunDetailView, { routePath: ROUTE, path: PATH })
    await clickButton('提缺陷')
    await typeInto(modalTitleInput(), '   ')
    await clickButton('确认提交')
    expect(document.body.textContent).toContain('请填写缺陷标题')
    expect(calls.some(c => c.method === 'POST')).toBe(false)
  })

  it('确认提交时 POST .../bug，带改过的标题和严重程度', async () => {
    const calls = mockApi(baseRoutes({
      'GET /runs/42/results/1/bug-draft': { title: '原标题', description: '描述', severity: 'normal' },
      'POST /runs/42/results/1/bug': { pmBugKey: 'FLEET-10' },
    }))
    const { wrapper } = await mountView(RunDetailView, { routePath: ROUTE, path: PATH })
    await clickButton('提缺陷')
    await typeInto(modalTitleInput(), '改过的标题')
    // 严重程度下拉在 jsdom 里不好点，直接改组件里的草稿（等同于用户选了「严重」）
    ;(wrapper.vm as any).bugModal.draft.severity = 'major'
    await flushPromises()
    await clickButton('确认提交')
    const post = calls.find(c => c.method === 'POST' && c.url === '/runs/42/results/1/bug')
    expect(post).toBeTruthy()
    expect(post!.body).toMatchObject({ title: '改过的标题', severity: 'major', description: '描述' })
  })
})