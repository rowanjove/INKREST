<script setup lang="ts">
import { Collection, Cpu, Lightning, Plus, User } from '@element-plus/icons-vue'
import type { TropeComponent, TropeSlotType, TropeTab } from '../../composables/useTropeWorkshop'

defineProps<{
  channels: TropeComponent[]
  themes: TropeComponent[]
  mechanisms: TropeComponent[]
  coolPoints: TropeComponent[]
  loading: boolean
  onAddToBlueprint: (item: TropeComponent, type: TropeSlotType) => void
  onDragStart: (event: DragEvent, item: TropeComponent, type: TropeSlotType) => void
}>()

const activeTab = defineModel<TropeTab>('activeTab', { required: true })
</script>

<template>
  <aside class="component-library">
    <div class="library-header">
      <h3>套路预设元件库</h3>
      <p>选中或向右侧拖拽卡片来进行拼装</p>
    </div>

    <el-tabs v-model="activeTab" class="library-tabs">
      <el-tab-pane name="channels" label="主角角色">
        <div class="component-grid" v-loading="loading">
          <div
            v-for="item in channels"
            :key="item.id"
            class="component-card card-channel"
            draggable="true"
            @dragstart="(e) => onDragStart(e, item, 'channels')"
            @click="onAddToBlueprint(item, 'channels')"
          >
            <div class="card-head">
              <span class="card-tag">主角</span>
              <el-icon class="card-icon"><User /></el-icon>
            </div>
            <h4>{{ item.name }}</h4>
            <p>{{ item.description }}</p>
            <div class="card-footer">
              <span class="card-id">#{{ item.id }}</span>
              <span class="card-add-btn" title="添加到工作台" aria-hidden="true">
                <el-icon><Plus /></el-icon>
              </span>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="themes" label="题材主题">
        <div class="component-grid" v-loading="loading">
          <div
            v-for="item in themes"
            :key="item.id"
            class="component-card card-theme"
            draggable="true"
            @dragstart="(e) => onDragStart(e, item, 'themes')"
            @click="onAddToBlueprint(item, 'themes')"
          >
            <div class="card-head">
              <span class="card-tag">主题</span>
              <el-icon class="card-icon"><Collection /></el-icon>
            </div>
            <h4>{{ item.name }}</h4>
            <p>{{ item.description }}</p>
            <div class="card-footer">
              <span class="card-id">#{{ item.id }}</span>
              <span class="card-add-btn" title="添加到工作台" aria-hidden="true">
                <el-icon><Plus /></el-icon>
              </span>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="mechanisms" label="剧情机制">
        <div class="component-grid" v-loading="loading">
          <div
            v-for="item in mechanisms"
            :key="item.id"
            class="component-card card-mechanism"
            draggable="true"
            @dragstart="(e) => onDragStart(e, item, 'mechanisms')"
            @click="onAddToBlueprint(item, 'mechanisms')"
          >
            <div class="card-head">
              <span class="card-tag">机制</span>
              <el-icon class="card-icon"><Cpu /></el-icon>
            </div>
            <h4>{{ item.name }}</h4>
            <p>{{ item.description }}</p>
            <div class="card-footer">
              <span class="card-id">#{{ item.id }}</span>
              <span class="card-add-btn" title="添加到工作台" aria-hidden="true">
                <el-icon><Plus /></el-icon>
              </span>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane name="cool_points" label="爽点节奏">
        <div class="component-grid" v-loading="loading">
          <div
            v-for="item in coolPoints"
            :key="item.id"
            class="component-card card-cool"
            draggable="true"
            @dragstart="(e) => onDragStart(e, item, 'cool_points')"
            @click="onAddToBlueprint(item, 'cool_points')"
          >
            <div class="card-head">
              <span class="card-tag">爽点</span>
              <el-icon class="card-icon"><Lightning /></el-icon>
            </div>
            <h4>{{ item.name }}</h4>
            <p>{{ item.description }}</p>
            <div class="card-footer">
              <span class="card-id">#{{ item.id }}</span>
              <span class="card-add-btn" title="添加到工作台" aria-hidden="true">
                <el-icon><Plus /></el-icon>
              </span>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </aside>
</template>

<style scoped>
.component-library {
  display: flex;
  flex-direction: column;
  padding: 20px;
  overflow: hidden;
  background: var(--color-bg-surface);
  border: 1px solid #e1e7ef;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
}

.library-header {
  margin-bottom: 12px;
}

.library-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 750;
  color: #1a202c;
}

.library-header p {
  margin: 4px 0 0;
  font-size: 13px;
  color: #718096;
}

.library-tabs {
  flex: 1;
  overflow: auto;
}

.component-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  max-height: calc(100vh - 350px);
  overflow-y: auto;
  padding-right: 4px;
}

.component-card {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 12px;
  background: var(--color-bg-surface-muted);
  cursor: grab;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  min-height: 140px;
}

.component-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border-color: var(--primary);
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.card-tag {
  font-size: 10px;
  font-weight: 750;
  padding: 2px 6px;
  border-radius: 4px;
}

.card-channel .card-tag { background: #e0f2fe; color: #0284c7; }
.card-theme .card-tag { background: #dcfce7; color: var(--color-success); }
.card-mechanism .card-tag { background: #fef3c7; color: var(--color-warning); }
.card-cool .card-tag { background: #f3e8ff; color: #9333ea; }

.card-icon {
  font-size: 14px;
  color: #a0aec0;
}

.component-card h4 {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 700;
  color: #2d3748;
}

.component-card p {
  margin: 0;
  font-size: 11.5px;
  color: #718096;
  line-height: 1.4;
  flex: 1;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-id {
  font-size: 10px;
  font-family: monospace;
  color: #a0aec0;
}

.card-add-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #ffffff;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(198, 111, 79, 0.38);
  border: 1.5px solid rgba(255, 255, 255, 0.55);
  transition: transform 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}

.card-add-btn .el-icon {
  font-size: 15px;
  font-weight: 700;
}

.component-card:hover .card-add-btn {
  background: var(--color-primary-hover);
  transform: scale(1.08);
  box-shadow: 0 3px 10px rgba(198, 111, 79, 0.45);
}
</style>