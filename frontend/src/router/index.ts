import type { Pinia } from 'pinia'
import type { Component } from 'vue'
import {
  createMemoryHistory,
  createRouter,
  createWebHistory,
  type Router,
} from 'vue-router'

import { bindUserStoreToHttp, useUserStore } from '../stores/user'

const testComponent: Component = { template: '<div />' }
const routeComponent = (loader: () => Promise<Component>) =>
  import.meta.env.MODE === 'test' ? testComponent : loader

export function createAppRouter(): Router {
  return createRouter({
    history: typeof window === 'undefined' ? createMemoryHistory() : createWebHistory(),
    routes: [
      {
        path: '/login',
        name: 'login',
        component: routeComponent(() => import('../views/LoginView.vue')),
        meta: { public: true },
      },
      {
        path: '/register',
        name: 'register',
        component: routeComponent(() => import('../views/RegisterView.vue')),
        meta: { public: true },
      },
      {
        path: '/workbench',
        name: 'workbench',
        component: routeComponent(() => import('../views/WorkbenchView.vue')),
        meta: { requiresAuth: true, title: '首页' },
      },
      {
        path: '/', name: 'home',
        component: routeComponent(() => import('../views/HomeView.vue')),
        meta: { requiresAuth: true, title: '首页' },
      },
      {
        path: '/chat', name: 'chat',
        component: routeComponent(() => import('../views/ChatView.vue')),
        meta: { requiresAuth: true, title: '多智能体对话' },
      },
      {
        path: '/resources', name: 'resources',
        component: routeComponent(() => import('../views/ResourcesView.vue')),
        meta: { requiresAuth: true, title: '学习资源库' },
      },
      {
        path: '/path', name: 'path',
        component: routeComponent(() => import('../views/PathView.vue')),
        meta: { requiresAuth: true, title: '学习路径' },
      },
      {
        path: '/tutor', name: 'tutor',
        component: routeComponent(() => import('../views/TutorView.vue')),
        meta: { requiresAuth: true, title: '智能辅导' },
      },
      {
        path: '/admin', name: 'admin',
        component: routeComponent(() => import('../views/AdminView.vue')),
        meta: { requiresAuth: true, title: '管理后台' },
      },
    ],
  })
}

export function installAuthGuard(router: Router, pinia: Pinia): void {
  const store = useUserStore(pinia)
  bindUserStoreToHttp(store)

  router.beforeEach(async (to) => {
    if (!store.sessionRestored) await store.restoreSession()

    if (to.path === '/') return store.isAuthenticated ? '/workbench' : '/login'

    if (to.meta.requiresAuth && !store.isAuthenticated) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }

    if (to.meta.public && store.isAuthenticated) return '/workbench'
  })
}
