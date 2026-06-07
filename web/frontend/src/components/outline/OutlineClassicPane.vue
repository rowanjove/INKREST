<script setup lang="ts">
defineProps<{
  outline: Record<string, any>
  title: string
  logline: string
  genre: string
  targetChapters: number
  protagonist: Record<string, any>
  promises: any[]
  arcs: any[]
  displayIndex: (index: string | number) => number
}>()
</script>

<template>
  <div class="classic-layout">
    <section class="main-panel">
      <div class="title-block">
        <span>{{ outline?.chosen_title ? '最终书名' : '候选书名' }}</span>
        <h2>{{ title }}</h2>
        <p class="logline-clamp">{{ logline }}</p>
      </div>

      <div class="info-grid">
        <article>
          <span>题材</span>
          <strong>{{ genre }}</strong>
        </article>
        <article>
          <span>篇幅</span>
          <strong>{{ targetChapters }} 章</strong>
        </article>
        <article>
          <span>主角</span>
          <strong>{{ protagonist.name || '未设定' }}</strong>
        </article>
        <article>
          <span>冲突</span>
          <strong>{{ outline.conflict || '未设定' }}</strong>
        </article>
      </div>

      <div class="text-pair">
        <section class="text-section">
          <h3>核心主题</h3>
          <p class="text-clamp">{{ outline.core_theme || '暂无' }}</p>
        </section>
        <section class="text-section">
          <h3>主角弧光</h3>
          <p class="text-clamp">{{ protagonist.arc || protagonist.description || '暂无' }}</p>
        </section>
      </div>
    </section>

    <aside class="side-panel">
      <h3>读者承诺</h3>
      <div v-if="promises.length" class="promise-list">
        <span v-for="item in promises" :key="item">{{ item }}</span>
      </div>
      <el-empty v-else description="暂无" :image-size="48" />
    </aside>

    <section class="arc-panel">
      <div class="section-head">
        <h3>卷纲 / 阶段</h3>
        <span>{{ arcs.length }} 阶段</span>
      </div>
      <div v-if="arcs.length" class="arc-scroll">
        <div class="arc-list">
          <article v-for="(arc, index) in arcs" :key="index" class="arc-card">
            <span>Phase {{ displayIndex(index) }}</span>
            <strong>{{ arc.title || arc.name || `阶段 ${displayIndex(index)}` }}</strong>
            <p>{{ arc.summary || arc.description || arc.goal || arc }}</p>
          </article>
        </div>
      </div>
      <el-empty v-else description="暂无阶段" :image-size="48" />
    </section>
  </div>
</template>

<style scoped>
.classic-layout {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 240px;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 10px;
}

.main-panel,
.side-panel,
.arc-panel {
  border: 1px solid #e1e7ef;
  border-radius: 8px;
  background: var(--color-bg-surface);
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
  padding: 12px 14px;
  min-height: 0;
}

.main-panel {
  grid-row: 1;
  grid-column: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow: hidden;
}

.side-panel {
  grid-row: 1;
  grid-column: 2;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.arc-panel {
  grid-column: 1 / -1;
  grid-row: 2;
  max-height: 168px;
  display: flex;
  flex-direction: column;
}

.title-block span,
.info-grid span,
.arc-card span {
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 700;
}

.title-block h2 {
  margin: 2px 0 0;
  color: #111827;
  font-size: 18px;
  line-height: 1.25;
}

.logline-clamp,
.text-clamp,
.arc-card p {
  color: var(--color-text-muted);
  line-height: 1.5;
  margin: 0;
  font-size: 13.5px;
}

.logline-clamp {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.info-grid article {
  padding: 8px 10px;
  border: 1px solid #e5eaf2;
  border-radius: 6px;
  background: var(--color-bg-surface-muted);
}

.info-grid strong {
  display: block;
  margin-top: 4px;
  color: #111827;
  font-size: 13.5px;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.text-pair {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  flex: 1;
  min-height: 0;
}

.text-section {
  padding: 8px 10px;
  border: 1px solid var(--color-border-subtle);
  border-radius: 6px;
  background: var(--color-bg-surface-muted);
  min-height: 0;
  overflow: hidden;
}

.text-section h3,
.side-panel h3,
.section-head h3 {
  margin: 0 0 4px;
  color: #111827;
  font-size: 13px;
}

.text-clamp {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.promise-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  overflow: auto;
  flex: 1;
  min-height: 0;
  align-content: flex-start;
}

.promise-list span {
  padding: 4px 8px;
  border-radius: 999px;
  background: #fff4ee;
  color: #a55236;
  font-size: 12.5px;
  font-weight: 650;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--color-text-muted);
  font-size: 12px;
  flex-shrink: 0;
  margin-bottom: 6px;
}

.arc-scroll {
  flex: 1;
  min-height: 0;
  overflow-x: auto;
  overflow-y: hidden;
}

.arc-list {
  display: flex;
  gap: 10px;
  padding-bottom: 4px;
}

.arc-card {
  flex: 0 0 220px;
  padding: 10px;
  border: 1px solid #e5eaf2;
  border-radius: 8px;
  background: var(--color-bg-surface);
}

.arc-card strong {
  display: block;
  margin: 4px 0;
  color: #111827;
  font-size: 13px;
}

.arc-card p {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

@media (max-width: 1280px) {
  .classic-layout {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto auto;
  }

  .side-panel {
    grid-column: 1;
    grid-row: 2;
    max-height: 100px;
  }

  .arc-panel {
    grid-row: 3;
  }

  .info-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>