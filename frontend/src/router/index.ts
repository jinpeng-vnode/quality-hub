import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/projects' },
    { path: '/login', name: 'Login', component: () => import('../views/LoginView.vue'), meta: { title: '登录', public: true } },
    { path: '/projects', name: 'Projects', component: () => import('../views/ProjectView.vue'), meta: { title: '项目管理' } },
    {
      path: '/projects/:projectId',
      children: [
        { path: 'features', name: 'Features', component: () => import('../views/FeatureView.vue'), meta: { title: '功能点管理' } },
        { path: 'cases', name: 'Cases', component: () => import('../views/TestCaseView.vue'), meta: { title: '测试用例' } },
        { path: 'runs', name: 'Runs', component: () => import('../views/ExecutionView.vue'), meta: { title: '执行管理' } },
        { path: 'runs/:runId', name: 'RunDetail', component: () => import('../views/RunDetailView.vue'), meta: { title: '执行详情' } },
        { path: 'report', name: 'Report', component: () => import('../views/ReportView.vue'), meta: { title: '报告看板' } },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('../views/NotFoundView.vue'), meta: { title: '404' } },
  ],
})

// 登录守卫：第一次进页面问一次后端当前是谁，没登录就去登录页
router.beforeEach(async (to) => {
  if (to.meta?.public) return true
  const auth = useAuthStore()
  if (!auth.checked) await auth.fetchMe()
  if (!auth.user) return { name: 'Login', query: { redirect: to.fullPath } }
  return true
})

// 动态设置 document.title
router.afterEach((to) => {
  const title = (to.meta?.title as string) || 'Quality Hub'
  document.title = `${title} - Quality Hub`
})

export default router
