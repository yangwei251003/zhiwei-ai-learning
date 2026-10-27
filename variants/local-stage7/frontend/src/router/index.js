import { createRouter, createWebHistory } from 'vue-router'

export const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { public: true } },
  { path: '/register', name: 'register', component: () => import('@/views/RegisterView.vue'), meta: { public: true } },
  { path: '/', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { requiresAuth: true } },
  { path: '/chat', name: 'chat', component: () => import('@/views/ChatView.vue'), meta: { requiresAuth: true } },
  { path: '/resources', name: 'resources', component: () => import('@/views/ResourcesView.vue'), meta: { requiresAuth: true } },
  { path: '/path', name: 'path', component: () => import('@/views/PathView.vue'), meta: { requiresAuth: true } },
  { path: '/tutor', name: 'tutor', component: () => import('@/views/TutorView.vue'), meta: { requiresAuth: true } },
  { path: '/admin', name: 'admin', component: () => import('@/views/AdminView.vue'), meta: { requiresAuth: true, requiresAdmin: true } },
]

export function createAppRouter(history = createWebHistory(), authenticated = () => Boolean(localStorage.getItem('xzxx-token'))) {
  const router = createRouter({ history, routes, scrollBehavior: () => ({ top: 0 }) })
  router.beforeEach((to) => {
    if (to.meta.requiresAuth && !authenticated()) {
      return { name: 'login', query: { redirect: to.fullPath } }
    }
    if (to.meta.public && authenticated()) return { name: 'home' }
    return true
  })
  return router
}

export default createAppRouter()
