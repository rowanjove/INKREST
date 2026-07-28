<script setup lang="ts">
import { MoreFilled } from '@element-plus/icons-vue'
import type { Project } from '../../stores/project'
import { lastEditLabel, lastEditTitle } from '../../utils/libraryFormatters'

type ProjectCommand =
  | 'open'
  | 'read'
  | 'details'
  | 'pin'
  | 'rename'
  | 'export-md'
  | 'export-docx'
  | 'export-txt'
  | 'delete'

const props = defineProps<{
  projects: Project[]
  pinningId: string | null
  getCoverStyle: (project: Project) => Record<string, string | undefined>
  onOpenProject: (id: string) => void
  onTogglePin: (project: Project, event: Event) => void
  onOpenPendingMaintenance: (project: Project, event: Event) => void
  onOpenDetails: (project: Project) => void
  onRename: (project: Project) => void
  onHandleRead: (id: string) => void
  onHandleDelete: (id: string, name: string) => void
  onHandleExportFormat: (format: string, project: Project) => void
}>()

function targetLabel(project: Project) {
  const target = Number(project.target_chapters || 0)
  return target > 0 ? `${project.chapter_count || 0} / ${target} 章` : `${project.chapter_count || 0} 章`
}

function handleCommand(command: ProjectCommand, project: Project) {
  if (command === 'open') props.onOpenProject(project.id)
  if (command === 'read') props.onHandleRead(project.id)
  if (command === 'details') props.onOpenDetails(project)
  if (command === 'pin') props.onTogglePin(project, new Event('menu'))
  if (command === 'rename') props.onRename(project)
  if (command === 'delete') props.onHandleDelete(project.id, project.name)
  if (command.startsWith('export-')) {
    props.onHandleExportFormat(command.replace('export-', ''), project)
  }
}
</script>

<template>
  <div class="project-grid">
    <article
      v-for="project in projects"
      :key="project.id"
      class="project-card"
      :class="{ 'is-pinned': project.pinned }"
      tabindex="0"
      @click="onOpenProject(project.id)"
      @keydown.enter="onOpenProject(project.id)"
    >
      <div
        class="project-cover"
        :class="{ 'has-cover': project.has_cover }"
        :style="getCoverStyle(project)"
        aria-hidden="true"
      >
        <span v-if="!project.has_cover">{{ project.name.slice(0, 1) }}</span>
      </div>

      <div class="project-copy">
        <div class="project-title-row">
          <div>
            <span v-if="project.pinned" class="pin-label">置顶</span>
            <h2>{{ project.name }}</h2>
            <p class="author">{{ project.author_label || '未设置作者' }}</p>
          </div>
          <el-dropdown
            trigger="click"
            @click.stop
            @command="(command: ProjectCommand) => handleCommand(command, project)"
          >
            <el-button
              text
              circle
              class="menu-button"
              :icon="MoreFilled"
              :aria-label="`${project.name} 的操作菜单`"
              @click.stop
            />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="open">打开策划</el-dropdown-item>
                <el-dropdown-item command="read">阅读成稿</el-dropdown-item>
                <el-dropdown-item command="details">作品资料与封面</el-dropdown-item>
                <el-dropdown-item command="pin" :disabled="pinningId === project.id">
                  {{ project.pinned ? '取消置顶' : '置顶作品' }}
                </el-dropdown-item>
                <el-dropdown-item command="rename">重命名</el-dropdown-item>
                <el-dropdown-item divided command="export-md">导出 Markdown</el-dropdown-item>
                <el-dropdown-item command="export-docx">导出 Word</el-dropdown-item>
                <el-dropdown-item command="export-txt">导出文本</el-dropdown-item>
                <el-dropdown-item divided command="delete">删除作品</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <div class="project-meta">
          <span>{{ targetLabel(project) }}</span>
          <span :title="lastEditTitle(project)">更新于 {{ lastEditLabel(project) }}</span>
        </div>

        <button
          v-if="(project.pending_alert_count || 0) > 0"
          type="button"
          class="risk-link"
          @click.stop="onOpenPendingMaintenance(project, $event)"
        >
          {{ project.pending_alert_count }} 项未解决风险
        </button>
        <span v-else class="risk-clear">暂无未解决风险</span>
      </div>
    </article>
  </div>
</template>

<style scoped>
.project-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--space-4);
}

.project-card {
  min-width: 0;
  display: grid;
  grid-template-columns: 88px minmax(0, 1fr);
  gap: var(--space-4);
  min-height: 148px;
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease;
}

.project-card:hover,
.project-card:focus-visible {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
  outline: none;
}

.project-card.is-pinned {
  border-color: color-mix(in srgb, var(--color-primary) 42%, var(--color-border));
}

.project-cover {
  display: grid;
  place-items: center;
  width: 88px;
  aspect-ratio: 2 / 3;
  overflow: hidden;
  border-radius: var(--radius-md);
  background: linear-gradient(145deg, var(--color-primary), #8b5e83);
  color: white;
  font-size: 28px;
  font-weight: 800;
  box-shadow: var(--shadow-sm);
}

.project-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.project-title-row {
  min-width: 0;
  display: flex;
  justify-content: space-between;
  gap: var(--space-2);
}

.project-title-row > div { min-width: 0; }

.project-title-row h2 {
  margin: 3px 0 0;
  overflow: hidden;
  color: var(--color-text-strong);
  font-size: 16px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pin-label {
  color: var(--color-primary);
  font-size: 11px;
  font-weight: 700;
}

.author {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 12px;
}

.menu-button { flex: none; }

.project-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px 12px;
  margin-top: auto;
  color: var(--color-text-muted);
  font-size: 12px;
}

.risk-link,
.risk-clear {
  align-self: flex-start;
  margin-top: var(--space-2);
  font-size: 12px;
}

.risk-link {
  padding: 0;
  border: 0;
  background: none;
  color: var(--color-danger);
  cursor: pointer;
}

.risk-clear { color: var(--color-success); }

@media (max-width: 720px) {
  .project-grid { grid-template-columns: 1fr; }
}
</style>
