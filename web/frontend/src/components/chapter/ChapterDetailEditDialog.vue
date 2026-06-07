<script setup lang="ts">
defineProps<{
  savingEdit: boolean
  editForm: { title: string; final_text: string }
}>()

const editDialogVisible = defineModel<boolean>('editDialogVisible', { required: true })

const emit = defineEmits<{
  saveEdit: []
}>()
</script>

<template>
  <el-dialog v-model="editDialogVisible" title="编辑章节" width="800px" destroy-on-close align-center>
    <el-form label-position="top">
      <el-form-item label="章节标题" required>
        <el-input v-model="editForm.title" placeholder="请输入章节标题" />
      </el-form-item>
      <el-form-item label="正文内容" required>
        <el-input
          v-model="editForm.final_text"
          type="textarea"
          :rows="18"
          placeholder="请输入正文内容..."
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingEdit" @click="emit('saveEdit')">保存修改</el-button>
      </span>
    </template>
  </el-dialog>
</template>