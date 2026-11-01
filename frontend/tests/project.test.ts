import { describe, it, expect, afterEach, vi } from 'vitest'
import { message } from 'ant-design-vue'
import ProjectView from '../src/views/ProjectView.vue'
import type { Project } from '../src/types'
import { mountView, mockApi, clickButton, flushPromises } from './helpers'

afterEach(() => { vi.restoreAllMocks(); document.body.innerHTML = '' })

const NOW = new Date().toISOString()
const PROJECTS: Project[] = [
  { id: 1, name: '多机协作工程', description: '舰队', pmProjectKey: 'FLEET', repoUrl: 'https://github.com/x/fleet', createdAt: NOW, updatedAt: NOW },
  { id: 2, name: '旧项目', description: null, pmProjectKey: null, repoUrl: null, createdAt: NOW, updatedAt: NOW },
]

async function typeInto(placeholder: string, value: string) {
  const el = document.body.querySelector<HTMLInputElement>(`input[placeholder="${placeholder}"]`)
  if (!el) throw new Error(`找不到输入框「${placeholder}」`)
  el.value = value
  el.dispatchEvent(new Event('input'))
  await flushPromises()
}

/** 弹窗底部的确定按钮（antd 的 primary 按钮），不依赖语言包里的文字 */
async function confirmModal() {
  const ok = document.body.querySelector<HTMLButtonElement>('.ant-modal-footer .ant-btn-primary')
  if (!ok) throw new Error('找不到弹窗的确定按钮')
  ok.click()
  await flushPromises()
}

async function openImport() {
  await clickButton('从项目管理导入')
  if (!document.body.querySelector('input[placeholder="FLEET"]')) throw new Error('导入弹窗没打开')
}

describe('项目页', () => {
  it('入口按钮叫「从项目管理导入」，卡片显示 pmProjectKey', async () => {
    mockApi({ 'GET /projects': PROJECTS })
    const { wrapper } = await mountView(ProjectView, { routePath: '/projects' })
    const buttons = Array.from(document.body.querySelectorAll('button')).map(b => b.textContent?.replace(/\s/g, ''))
    expect(buttons).toContain('从项目管理导入')
    const text = wrapper.text()
    expect(text).toContain('多机协作工程')
    expect(text).toContain('FLEET')
    // 没有 pmProjectKey 的卡片不画链接标记
    expect(wrapper.findAll('.project-meta')[1].text()).not.toContain('🔗')
  })

  it.each(['', 'F', '1FLEET', 'FLEET-1', 'ABCDEFGHIJK'])('项目标识「%s」格式不对时提示，不发请求', async (bad) => {
    const calls = mockApi({ 'GET /projects': [], 'POST /projects/import': {} })
    const warn = vi.spyOn(message, 'warning')
    await mountView(ProjectView, { routePath: '/projects' })
    await openImport()
    await typeInto('FLEET', bad)
    await confirmModal()
    expect(warn).toHaveBeenCalledWith('项目标识应为 2～10 位大写字母或数字，以字母开头')
    expect(calls.filter(c => c.method === 'POST')).toHaveLength(0)
  })

  it('格式对时 POST /projects/import，小写转大写、带 repoUrl，成功后刷新列表', async () => {
    let listed: Project[] = []
    const calls = mockApi({
      'GET /projects': () => listed,
      'POST /projects/import': (body: any) => {
        listed = [{ id: 3, name: '质量中心', description: null, pmProjectKey: body.pmProjectKey, repoUrl: body.repoUrl, createdAt: NOW, updatedAt: NOW }]
        return listed[0]
      },
    })
    const { wrapper } = await mountView(ProjectView, { routePath: '/projects' })
    await openImport()
    await typeInto('FLEET', ' qhub2 ')
    await typeInto('GitHub 仓库 URL', 'https://github.com/jinpeng-vnode/quality-hub')
    await confirmModal()
    const posts = calls.filter(c => c.method === 'POST')
    expect(posts).toEqual([{
      method: 'POST', url: '/projects/import',
      body: { pmProjectKey: 'QHUB2', repoUrl: 'https://github.com/jinpeng-vnode/quality-hub' }, params: undefined,
    }])
    expect(calls.filter(c => c.url === '/projects' && c.method === 'GET')).toHaveLength(2)
    expect(wrapper.text()).toContain('QHUB2')
  })

  it('不填仓库地址时 body 里不带 repoUrl 的值', async () => {
    const calls = mockApi({ 'GET /projects': [], 'POST /projects/import': {} })
    await mountView(ProjectView, { routePath: '/projects' })
    await openImport()
    await typeInto('FLEET', 'FLEET')
    await confirmModal()
    const post = calls.find(c => c.method === 'POST')
    expect(post?.body.pmProjectKey).toBe('FLEET')
    expect(post?.body.repoUrl).toBeUndefined()
  })
})
