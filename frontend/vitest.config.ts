import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

// 前端组件测试：jsdom 环境，接口一律用 tests/helpers 里的假 api，不连后端
export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    include: ['tests/**/*.test.ts'],
    setupFiles: ['tests/setup.ts'],
    // 路由守卫测试会真的加载懒加载页面（报告页带 echarts），并行时首次编译可能超过默认的 5 秒
    testTimeout: 30000,
  },
})
