#!/usr/bin/env node
// quality-hub 前端一键检查：类型检查 → 组件测试 → 打包。只输出结论和失败原文。
// 用法（仓库根目录）：node scripts/ui-check.mjs
// 前提：frontend 下已安装依赖（yarn install --frozen-lockfile）
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const fe = path.join(path.dirname(fileURLToPath(import.meta.url)), '..', 'frontend')
const bin = (n) => path.join(fe, 'node_modules', '.bin', process.platform === 'win32' ? `${n}.cmd` : n)
const steps = [
  ['类型检查', bin('vue-tsc'), ['--noEmit', '-p', 'tsconfig.app.json']],
  ['组件测试', bin('vitest'), ['run', '--reporter=dot']],
  ['打包', bin('vite'), ['build', '--logLevel', 'error']],
]
let failed = 0
for (const [name, cmd, args] of steps) {
  const r = spawnSync(cmd, args, { cwd: fe, encoding: 'utf8', shell: process.platform === 'win32', env: { ...process.env, FORCE_COLOR: '0' } })
  if (r.status === 0) {
    const m = name === '组件测试' ? (r.stdout.match(/Tests\s+(.+)/) || [])[1] : ''
    console.log(`✅ ${name}${m ? '：' + m.trim() : ''}`)
  } else {
    failed++
    console.log(`❌ ${name}（退出码 ${r.status}）`)
    console.log(((r.stdout || '') + (r.stderr || '')).trim().split('\n').slice(-40).join('\n'))
  }
}
console.log(failed ? `结论：${failed} 项失败` : '结论：全部通过')
process.exit(failed ? 1 : 0)
