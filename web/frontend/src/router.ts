import { createRouter, createWebHistory } from 'vue-router'
import { appScrollBehavior, routeFallback } from './app/router/routeMeta'
import { useProjectStore } from './stores/project'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: appScrollBehavior,
  routes: [
    { path: '/', name: 'library', component: () => import('./views/LibraryView.vue'), meta: { scope: 'global', title: '书库', navId: 'library' } },
    { path: '/onboarding', redirect: '/create?welcome=1', meta: { scope: 'global', title: '新建作品', navId: 'create' } },
    { path: '/create', name: 'create', component: () => import('./views/CreateWizard.vue'), meta: { scope: 'global', title: '新建作品', navId: 'create' } },
    { path: '/reader', name: 'reader', component: () => import('./views/ReaderView.vue'), meta: { scope: 'project', title: '发布', navId: 'publishing', fullBleed: true } },
    { path: '/workspace', name: 'dashboard', component: () => import('./views/Dashboard.vue'), meta: { scope: 'project', title: '概览', navId: 'overview' } },
    { path: '/outline', name: 'outline', component: () => import('./views/OutlineView.vue'), meta: { scope: 'project', title: '策划', navId: 'planning', fullBleed: true } },
    { path: '/chapters', redirect: '/writer', meta: { scope: 'project', title: '正文', navId: 'manuscript' } },
    { path: '/chapters/list', redirect: '/writer', meta: { scope: 'project', title: '正文', navId: 'manuscript' } },
    {
      path: '/chapters/maintenance',
      name: 'chapters-maintenance',
      component: () => import('./views/ChapterMaintenance.vue'),
      meta: { scope: 'project', title: '章节维护', navId: 'production' },
    },
    {
      path: '/chapters/:id',
      name: 'chapter-detail',
      redirect: (to) => ({ path: '/writer', query: { chapter: String(to.params.id) } }),
      meta: { scope: 'project', title: '正文', navId: 'manuscript' },
    },
    { path: '/state', name: 'state', component: () => import('./views/StateView.vue'), meta: { scope: 'project', title: '剧情状态', navId: 'planning' } },
    { path: '/assets', name: 'assets', component: () => import('./views/AssetEditor.vue'), meta: { scope: 'project', title: '故事素材', navId: 'planning' } },
    { path: '/monitor', name: 'monitor', component: () => import('./views/MonitorView.vue'), meta: { scope: 'project', title: '生产', navId: 'production' } },
    { path: '/tasks', redirect: '/chapters/maintenance', meta: { scope: 'project', title: '任务', navId: 'production' } },
    { path: '/logs', redirect: '/monitor?tab=logs', meta: { scope: 'project', title: '日志', navId: 'production' } },
    { path: '/config', name: 'config', component: () => import('./views/ConfigView.vue'), meta: { scope: 'global', title: '设置', navId: 'settings' } },
    { path: '/writer', name: 'writer', component: () => import('./views/WritingWorkspace.vue'), meta: { scope: 'project', title: '正文', navId: 'manuscript', fullBleed: true } },
    { path: '/plugins', name: 'plugins', component: () => import('./views/PluginManager.vue'), meta: { scope: 'global', title: '扩展', navId: 'extensions' } },
    { path: '/pet', name: 'pet', component: () => import('./views/PetView.vue'), meta: { scope: 'pet', title: '杉杉', fullBleed: true } },
    { path: '/pet-bubble', name: 'pet-bubble', component: () => import('./views/PetBubbleView.vue'), meta: { scope: 'pet', title: '杉杉助手', fullBleed: true } },
    { path: '/trope-workshop', redirect: '/create?source=template', meta: { scope: 'global', title: '新建作品', navId: 'create' } },
  ],
})

router.beforeEach(async (to) => {
  if (to.meta.scope === 'pet') return true
  const projectStore = useProjectStore()
  await projectStore.hydrate()
  return routeFallback(to.meta.scope, Boolean(projectStore.currentProject?.id))
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 栖墨` : '栖墨'
})

export default router
