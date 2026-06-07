<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection } from '@element-plus/icons-vue'
import { getConfig, updateConfig } from '../api'

const loading = ref(false)
const saving = ref(false)
const proxy = ref('')
const config = ref<Record<string, any>>({})

const load = async () => {
  loading.value = true
  try {
    const { data } = await getConfig()
    config.value = data
    proxy.value = data?.llm?.default?.proxy || data?.llm?.proxy || ''
  } catch (error: any) {
    ElMessage.error(error.message || '获取代理设置失败')
  } finally {
    loading.value = false
  }
}

const save = async () => {
  saving.value = true
  try {
    const llm = { ...(config.value.llm || {}) }
    llm.default = { ...(llm.default || {}), proxy: proxy.value.trim() }
    await updateConfig({ llm })
    ElMessage.success('代理设置已保存')
    await load()
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="proxy-card" v-loading="loading">
    <div class="proxy-head">
      <span class="proxy-icon"><el-icon><Connection /></el-icon></span>
      <div>
        <h2>网络代理</h2>
        <p>默认 LLM 请求代理</p>
      </div>
    </div>
    <div class="proxy-form">
      <el-input v-model="proxy" placeholder="http://127.0.0.1:7890" clearable />
      <el-button type="primary" :loading="saving" @click="save">保存代理</el-button>
    </div>
  </section>
</template>

<style scoped>
.proxy-card {
  display: grid;
  grid-template-columns: minmax(220px, 0.34fr) minmax(0, 0.66fr);
  align-items: center;
  gap: 18px;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: var(--color-bg-surface);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.05);
}

.proxy-head {
  display: flex;
  align-items: center;
  gap: 12px;
}

.proxy-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #eef6fb;
  color: #2f6f90;
}

.proxy-head h2 {
  margin: 0;
  color: var(--color-text-strong);
  font-size: 16px;
}

.proxy-head p {
  margin: 3px 0 0;
  color: var(--color-text-muted);
  font-size: 12px;
}

.proxy-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
}

@media (max-width: 960px) {
  .proxy-card,
  .proxy-form {
    grid-template-columns: 1fr;
  }
}
</style>
