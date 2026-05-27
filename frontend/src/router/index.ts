import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/projects' },
    { path: '/projects', name: 'Projects', component: () => import('../views/ProjectView.vue'), meta: { title: '项目管理' } },
    {
      path: '/projects/:projectId',
      children: [
        { path: 'features', name: 'Features', component: () => import('../views/FeatureView.vue'), meta: { title: '功能点管理' } },
        { path: 'cases', name: 'Cases', component: () => import('../views/TestCaseView.vue'), meta: { title: '测试用例' } },
        { path: 'runs', name: 'Runs', component: () => import('../views/ExecutionView.vue'), meta: { title: '执行管理' } },
        { path: 'report', name: 'Report', component: () => import('../views/ReportView.vue'), meta: { title: '报告看板' } },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'NotFound', component: () => import('../views/NotFoundView.vue'), meta: { title: '404' } },
  ],
})

// 动态设置 document.title
router.afterEach((to) => {
  const title = (to.meta?.title as string) || 'Quality Hub'
  document.title = `${title} - Quality Hub`
})

export default router
