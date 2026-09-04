<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Check, Collection, Document, Plus, Search } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { type Project, useProjectStore } from '../../stores/project'
import { formatDate, formatWords } from '../../utils/libraryFormatters'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const router = useRouter()
const projectStore = useProjectStore()

const visible = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val),
})

const searchQuery = ref('')
const switchingId = ref<string | null>(null)

watch(
  () => props.modelValue,
  (isOpen) => {
    if (isOpen) {
      searchQuery.value = ''
      if (projectStore.projects.length === 0) {
        void projectStore.fetchProjects()
      }
    }
  },
)

onMounted(() => {
  if (props.modelValue && projectStore.projects.length === 0) {
    void projectStore.fetchProjects()
  }
})

const filteredProjects = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()
  if (!query) return projectStore.projects
  return projectStore.projects.filter(
    (p) =>
      p.name.toLowerCase().includes(query) ||
      (p.description && p.description.toLowerCase().includes(query)) ||
      (p.genre && p.genre.toLowerCase().includes(query)),
  )
})

async function handleSelect(project: Project) {
  if (project.id === projectStore.currentProject?.id) {
    visible.value = false
    return
  }

  switchingId.value = project.id
  try {
    await projectStore.switchProject(project.id)
    ElMessage.success(`已切换至《${project.name}》`)
    visible.value = false
    window.dispatchEvent(new CustomEvent('inkrest-project-switched', { detail: { id: project.id } }))
  } catch {
    ElMessage.error('切换作品失败，请重试')
  } finally {
    switchingId.value = null
  }
}

function handleGoLibrary() {
  visible.value = false
  void router.push('/')
}

function handleGoCreate() {
  visible.value = false
  void router.push('/create')
}
</script>

<template>
  <el-dialog
    v-model="visible"
    title="切换创作作品"
    width="560px"
    destroy-on-close
    class="project-switcher-dialog"
    append-to-body
  >
    <div class="switcher-content">
      <div class="search-wrap">
        <el-input
          v-model="searchQuery"
          placeholder="搜索作品名称、题材或简介…"
          :prefix-icon="Search"
          clearable
          size="large"
          class="search-input"
          autofocus
        />
      </div>

      <div class="project-list-wrap">
        <div v-if="filteredProjects.length === 0" class="empty-hint">
          <p v-if="searchQuery">未找到与“{{ searchQuery }}”相关的作品</p>
          <p v-else>暂无其他作品，点击下方按钮开始创作</p>
        </div>

        <ul v-else class="project-list" role="listbox">
          <li
            v-for="project in filteredProjects"
            :key="project.id"
            class="project-item"
            :class="{
              'project-item--active': project.id === projectStore.currentProject?.id,
              'project-item--switching': switchingId === project.id,
            }"
            role="option"
            :aria-selected="project.id === projectStore.currentProject?.id"
            @click="handleSelect(project)"
          >
            <div class="item-icon">
              <Document />
            </div>

            <div class="item-main">
              <div class="item-title-row">
                <span class="item-name" :title="project.name">{{ project.name }}</span>
                <el-tag
                  v-if="project.id === projectStore.currentProject?.id"
                  size="small"
                  type="primary"
                  effect="plain"
                  round
                >
                  当前作品
                </el-tag>
              </div>

              <div class="item-meta">
                <span>{{ project.chapter_count ?? 0 }} 章</span>
                <span class="separator">•</span>
                <span>{{ formatWords(project.total_words ?? 0) }}</span>
                <template v-if="project.updated_at || project.activity_at">
                  <span class="separator">•</span>
                  <span>{{ formatDate(project.activity_at || project.updated_at || '') }}</span>
                </template>
              </div>
            </div>

            <div class="item-action">
              <el-icon v-if="project.id === projectStore.currentProject?.id" class="check-icon">
                <Check />
              </el-icon>
              <span v-else class="switch-hint">切换</span>
            </div>
          </li>
        </ul>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button text :icon="Collection" @click="handleGoLibrary">
          完整书库
        </el-button>
        <el-button type="primary" :icon="Plus" @click="handleGoCreate">
          新建小说
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.switcher-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-wrap {
  position: sticky;
  top: 0;
  z-index: 2;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: var(--radius-md, 8px);
}

.project-list-wrap {
  max-height: 360px;
  overflow-y: auto;
  padding-right: 4px;
}

.empty-hint {
  padding: 36px 0;
  text-align: center;
  color: var(--color-text-muted, #8c827a);
  font-size: 13.5px;
}

.project-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.project-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 14px;
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--color-border-subtle, rgba(0, 0, 0, 0.06));
  background: var(--color-bg-surface, #fff);
  cursor: pointer;
  transition: all 0.2s ease;
}

.project-item:hover {
  background: var(--color-bg-surface-hover, #f8f6f2);
  border-color: var(--color-primary-light, rgba(198, 111, 79, 0.3));
  transform: translateY(-1px);
}

.project-item--active {
  background: linear-gradient(180deg, rgba(198, 111, 79, 0.08) 0%, rgba(198, 111, 79, 0.03) 100%);
  border-color: rgba(198, 111, 79, 0.45);
}

.project-item--active:hover {
  background: linear-gradient(180deg, rgba(198, 111, 79, 0.12) 0%, rgba(198, 111, 79, 0.06) 100%);
}

.item-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  background: rgba(198, 111, 79, 0.1);
  color: var(--color-primary, #c66f4f);
  font-size: 18px;
  flex-shrink: 0;
}

.item-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.item-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.item-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-main, #2c2523);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--color-text-muted, #8c827a);
}

.separator {
  color: var(--color-border, #e2ded9);
}

.item-action {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  font-size: 13px;
}

.check-icon {
  font-size: 18px;
  color: var(--color-primary, #c66f4f);
}

.switch-hint {
  color: var(--color-text-subtle, #a09891);
  opacity: 0;
  transition: opacity 0.2s ease;
}

.project-item:hover .switch-hint {
  opacity: 1;
  color: var(--color-primary, #c66f4f);
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
}
</style>
