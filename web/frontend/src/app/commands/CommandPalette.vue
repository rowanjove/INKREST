<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'
import type { InputInstance } from 'element-plus'
import { useRouter } from 'vue-router'

import { getState, listChapters } from '../../api'
import { useProjectStore } from '../../stores/project'
import { useProjectSnapshotStore } from '../../stores/projectSnapshot'
import {
  buildNavigationCommands,
  commandFromSnapshotAction,
  commandsFromChapters,
  commandsFromCharacters,
  searchCommands,
  type AppCommand,
} from './commandRegistry'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
const router = useRouter()
const projectStore = useProjectStore()
const snapshotStore = useProjectSnapshotStore()
const query = ref('')
const dynamicCommands = ref<AppCommand[]>([])
const selectedIndex = ref(0)
const loading = ref(false)
const loadError = ref('')
const input = ref<InputInstance>()

const open = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const commands = computed(() => {
  const base = buildNavigationCommands(Boolean(projectStore.currentProject?.id))
  const nextActions =
    snapshotStore.snapshot?.next_actions.map(commandFromSnapshotAction) || []
  return [...nextActions, ...base, ...dynamicCommands.value]
})
const results = computed(() => searchCommands(commands.value, query.value))
const groupedResults = computed(() => {
  const groups = new Map<AppCommand['group'], Array<{ command: AppCommand; index: number }>>()
  results.value.forEach((command, index) => {
    const entries = groups.get(command.group) || []
    entries.push({ command, index })
    groups.set(command.group, entries)
  })
  return [...groups.entries()].map(([group, entries]) => ({ group, entries }))
})

type UnknownRecord = Record<string, unknown>

function recordArray(value: unknown, key?: string): UnknownRecord[] {
  if (Array.isArray(value)) return value.filter((item): item is UnknownRecord => typeof item === 'object' && item !== null)
  if (key && typeof value === 'object' && value !== null) {
    const nested = (value as UnknownRecord)[key]
    if (Array.isArray(nested)) {
      return nested.filter((item): item is UnknownRecord => typeof item === 'object' && item !== null)
    }
  }
  return []
}

async function loadProjectCommands() {
  if (!projectStore.currentProject?.id) {
    dynamicCommands.value = []
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    const [chaptersResponse, stateResponse] = await Promise.all([
      listChapters({ offset: 0, limit: 500, sync: false, include_gaps: false }),
      getState({ sync: false }),
    ])
    const chapters = recordArray(chaptersResponse.data, 'items').map((item) => ({
      chapter_id: String(item.chapter_id || item.id || ''),
      title: typeof item.title === 'string' ? item.title : undefined,
    })).filter((item) => item.chapter_id)
    const characters = recordArray(stateResponse.data, 'characters').map((item) => ({
      id: String(item.id || item.name || ''),
      name: typeof item.name === 'string' ? item.name : undefined,
    })).filter((item) => item.id)
    dynamicCommands.value = [
      ...commandsFromChapters(chapters),
      ...commandsFromCharacters(characters),
    ]
  } catch (error: unknown) {
    loadError.value = error instanceof Error ? error.message : '项目索引加载失败'
  } finally {
    loading.value = false
  }
}

async function execute(command: AppCommand | undefined) {
  if (!command || command.disabled) return
  open.value = false
  await router.push(command.path)
}

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    selectedIndex.value = results.value.length
      ? (selectedIndex.value + 1) % results.value.length
      : 0
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    selectedIndex.value = results.value.length
      ? (selectedIndex.value - 1 + results.value.length) % results.value.length
      : 0
  } else if (event.key === 'Enter') {
    event.preventDefault()
    void execute(results.value[selectedIndex.value])
  }
}

watch(query, () => {
  selectedIndex.value = 0
})

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) return
    query.value = ''
    selectedIndex.value = 0
    void loadProjectCommands()
    void nextTick(() => input.value?.focus())
  },
)
</script>

<template>
  <el-dialog
    v-model="open"
    class="command-palette"
    width="min(680px, calc(100vw - 32px))"
    :show-close="false"
    :close-on-click-modal="true"
    append-to-body
    @keydown="onKeydown"
  >
    <template #header>
      <div class="command-search">
        <el-icon aria-hidden="true"><Search /></el-icon>
        <el-input
          ref="input"
          v-model="query"
          aria-label="搜索页面、章节、人物或命令"
          placeholder="搜索页面、章节、人物或命令…"
          clearable
        />
        <kbd>Esc</kbd>
      </div>
    </template>

    <div class="command-results" role="listbox" aria-label="命令结果">
      <section v-for="group in groupedResults" :key="group.group" class="command-group">
        <h3>{{ group.group }}</h3>
        <button
          v-for="{ command, index } in group.entries"
          :key="command.id"
          type="button"
          class="command-result"
          :class="{ selected: index === selectedIndex }"
          role="option"
          :aria-selected="index === selectedIndex"
          @mouseenter="selectedIndex = index"
          @click="execute(command)"
        >
          <span class="command-result__copy">
            <strong>{{ command.label }}</strong>
            <small>{{ command.description }}</small>
          </span>
          <kbd v-if="index === selectedIndex">↵</kbd>
        </button>
      </section>
      <div v-if="!results.length && !loading" class="command-empty">
        没有匹配结果
      </div>
      <div v-if="loading" class="command-empty">正在读取项目索引…</div>
      <div v-if="loadError" class="command-load-error">
        项目索引暂不可用，页面命令仍可使用
      </div>
    </div>
    <footer class="command-help">
      <span>↑↓ 选择</span><span>Enter 打开</span><span>Esc 关闭</span>
    </footer>
  </el-dialog>
</template>

<style>
.command-palette .el-dialog__header {
  margin: 0;
  padding: 14px 16px;
  border-bottom: 1px solid var(--color-border-subtle);
}

.command-palette .el-dialog__body {
  padding: 8px;
}

.command-search {
  display: flex;
  align-items: center;
  gap: 10px;
}

.command-search .el-input__wrapper {
  padding: 0;
  box-shadow: none !important;
  background: transparent;
}

.command-search kbd,
.command-result kbd {
  padding: 2px 6px;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  color: var(--color-text-subtle);
  font: inherit;
  font-size: 11px;
}

.command-results {
  max-height: min(520px, 60vh);
  overflow-y: auto;
}

.command-group h3 {
  margin: 10px 11px 4px;
  color: var(--color-text-subtle);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
}

.command-result {
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  padding: 10px 11px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--color-text);
  cursor: pointer;
  text-align: left;
}

.command-result.selected {
  background: var(--color-primary-soft);
}

.command-result__copy strong,
.command-result__copy small {
  display: block;
}

.command-result__copy small {
  margin-top: 2px;
  color: var(--color-text-muted);
  font-size: 12px;
}

.command-empty,
.command-load-error {
  padding: 28px 16px;
  color: var(--color-text-muted);
  text-align: center;
}

.command-load-error {
  padding: 8px 16px;
  color: var(--color-warning);
  font-size: 12px;
}

.command-help {
  display: flex;
  gap: 16px;
  padding: 9px 12px 2px;
  border-top: 1px solid var(--color-border-subtle);
  color: var(--color-text-subtle);
  font-size: 11px;
}
</style>
