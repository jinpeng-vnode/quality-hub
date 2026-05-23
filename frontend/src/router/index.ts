import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/projects' },
    { path: '/projects', name: 'Projects', component: () => import('../views/ProjectView.vue') },
    {
      path: '/projects/:projectId',
      children: [
        { path: 'features', name: 'Features', component: () => import('../views/FeatureView.vue') },
        { path: 'cases', name: 'Cases', component: () => import('../views/TestCaseView.vue') },
        { path: 'runs', name: 'Runs', component: () => import('../views/ExecutionView.vue') },
        { path: 'report', name: 'Report', component: () => import('../views/ReportView.vue') },
      ],
    },
  ],
})

export default router
