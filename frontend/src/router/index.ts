import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/projects' },
    { path: '/projects', name: 'Projects', component: () => import('../views/ProjectView.vue') },
    { path: '/features', name: 'Features', component: () => import('../views/FeatureView.vue') },
    { path: '/testcases', name: 'TestCases', component: () => import('../views/TestCaseView.vue') },
    { path: '/executions', name: 'Executions', component: () => import('../views/ExecutionView.vue') },
    { path: '/reports', name: 'Reports', component: () => import('../views/ReportView.vue') },
  ],
})

export default router
