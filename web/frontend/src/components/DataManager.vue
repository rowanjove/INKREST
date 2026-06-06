<script setup lang="ts">
import { ref } from 'vue'
import { clearDatabase } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const clearing = ref(false)
const confirmText = ref('')
const expanded = ref(false)

const handleClear = async () => {
  try {
    await ElMessageBox.confirm(
      '此操作将永久删除所有数据（人物、事件、伏笔、章节记录等），且无法恢复。确定要继续吗？',
      '危险操作确认',
      {
        confirmButtonText: '确认清空',
        cancelButtonText: '取消',
        type: 'error',
        confirmButtonClass: 'el-button--danger',
      },
    )
    // Second confirmation: type "CLEAR"
    await ElMessageBox.prompt(
      '请输入 CLEAR 确认清空操作',
      '二次确认',
      {
        confirmButtonText: '执行清空',
        cancelButtonText: '取消',
        inputPattern: /^CLEAR$/,
        inputErrorMessage: '请输入 CLEAR',
        type: 'error',
      },
    )
    clearing.value = true
    await clearDatabase()
    ElMessage.success('数据库已清空')
    confirmText.value = ''
  } catch (e: any) {
    if (e !== 'cancel' && e?.action !== 'cancel') {
      ElMessage.error(e.message || '操作失败')
    }
  } finally {
    clearing.value = false
  }
}
</script>

<template>
  <section class="fold-card" style="margin-bottom: 20px">
    <div class="fold-head" @click="expanded = !expanded">
      <div class="head-left">
        <span class="collapse-arrow" :class="{ open: expanded }">▶</span>
        <div>
          <h2>数据管理</h2>
          <p>维护和清理项目数据库。</p>
        </div>
      </div>
    </div>
    
    <div v-show="expanded" class="fold-body">
      <div class="danger-zone">
        <div class="danger-header">
          <h4>清空数据库</h4>
          <p>删除所有生成数据，包括人物、事件、伏笔、钩子、章节记录等。此操作不可逆。</p>
        </div>
        <el-button
          type="danger"
          :loading="clearing"
          @click="handleClear"
        >
          清空所有数据
        </el-button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.danger-zone {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border: 1px solid #f56c6c;
  border-radius: 8px;
  background: #fef0f0;
  margin-top: 10px;
}
.danger-header h4 {
  font-size: 14px;
  color: #f56c6c;
  margin-bottom: 4px;
}
.danger-header p {
  font-size: 12px;
  color: #909399;
  margin: 0;
}
</style>

