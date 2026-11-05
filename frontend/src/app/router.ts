import { createRouter, createWebHistory } from 'vue-router'
import { useSession } from './session'
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/projects' },
    {
      path: '/login',
      component: () => import('../features/auth/AuthPage.vue'),
      meta: { public: true },
    },
    {
      path: '/register',
      component: () => import('../features/auth/AuthPage.vue'),
      meta: { public: true },
    },
    {
      path: '/admin/users',
      component: () => import('../features/settings/AdminUsersPage.vue'),
      meta: { admin: true },
    },
    {
      path: '/projects/:projectId/settings',
      component: () => import('../features/settings/ProjectSettingsPage.vue'),
    },
    {
      path: '/projects/:projectId/boards/:boardId/settings',
      component: () => import('../features/settings/BoardSettingsPage.vue'),
    },
    {
      path: '/projects/:projectId/analytics',
      component: () => import('../features/analytics/AnalyticsPage.vue'),
    },
    { path: '/projects', component: () => import('../features/projects/ProjectsPage.vue') },
    {
      path: '/projects/:projectId',
      component: () => import('../features/projects/ProjectPage.vue'),
    },
    {
      path: '/projects/:projectId/boards/:boardId',
      component: () => import('../features/board/BoardPage.vue'),
    },
    { path: '/tasks/:taskId', component: () => import('../features/task/TaskLinkPage.vue') },
    { path: '/:pathMatch(.*)*', component: () => import('../features/NotFoundPage.vue') },
  ],
})
router.beforeEach(async (to) => {
  if (to.meta.public) return
  const session = useSession()
  try {
    await session.restore(true)
  } catch {
    if (!session.user) return { path: '/login', query: { returnTo: to.fullPath, unavailable: '1' } }
  }
  if (!session.user) return { path: '/login', query: { returnTo: to.fullPath } }
  if (to.meta.admin && session.user.role !== 'admin') return '/projects'
})
router.afterEach((to) => {
  document.title = `${to.path === '/login' ? 'Вход' : to.path === '/register' ? 'Регистрация' : 'Рабочее пространство'} · Internal Task Tracker`
})
