import { createRouter, createWebHistory } from 'vue-router'
import { useProjectStore } from './stores/project'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'library', component: () => import('./views/LibraryView.vue') },
    { path: '/create', name: 'create', component: () => import('./views/CreateWizard.vue') },
    { path: '/reader', name: 'reader', component: () => import('./views/ReaderView.vue') },
    { path: '/workspace', name: 'dashboard', component: () => import('./views/Dashboard.vue') },
    { path: '/outline', name: 'outline', component: () => import('./views/OutlineView.vue') },
    {
      path: '/chapters',
      component: () => import('./views/ChaptersLayout.vue'),
      children: [
        { path: '', redirect: { name: 'chapters-list' } },
        {
          path: 'list',
          name: 'chapters-list',
          component: () => import('./views/ChapterList.vue'),
        },
        {
          path: 'maintenance',
          name: 'chapters-maintenance',
          component: () => import('./views/ChapterMaintenance.vue'),
        },
      ],
    },
    {
      path: '/chapters/:id',
      name: 'chapter-detail',
      component: () => import('./views/ChapterDetail.vue'),
    },
    { path: '/state', name: 'state', component: () => import('./views/StateView.vue') },
    { path: '/assets', name: 'assets', component: () => import('./views/AssetEditor.vue') },
    { path: '/monitor', name: 'monitor', component: () => import('./views/MonitorView.vue') },
    { path: '/tasks', redirect: '/chapters/maintenance' },
    { path: '/logs', redirect: '/monitor?tab=logs' },
    { path: '/config', name: 'config', component: () => import('./views/ConfigView.vue') },
    { path: '/writer', name: 'writer', component: () => import('./views/WritingWorkspace.vue') },
    { path: '/plugins', name: 'plugins', component: () => import('./views/PluginManager.vue') },
    { path: '/pet', name: 'pet', component: () => import('./views/PetView.vue') },
    { path: '/pet-bubble', name: 'pet-bubble', component: () => import('./views/PetBubbleView.vue') },
    { path: '/trope-workshop', name: 'trope-workshop', component: () => import('./views/TropeWorkshop.vue') },
  ],
})

// Redirect to library if no project is active (except library, create, trope-workshop & plugins pages)
router.beforeEach((to) => {
  if (
    to.name === 'library' ||
    to.name === 'create' ||
    to.name === 'config' ||
    to.name === 'plugins' ||
    to.name === 'pet' ||
    to.name === 'pet-bubble' ||
    to.name === 'trope-workshop'
  ) return true
  const projectStore = useProjectStore()
  if (!projectStore.currentProject?.id) {
    return { name: 'library' }
  }
  return true
})

export default router
