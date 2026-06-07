<script setup lang="ts">
defineProps<{
  outline: Record<string, any> | null
  submitting: boolean
  tasksRunning: boolean
  onSubmitOutline: () => void
  onSaveOutlineBasics: () => void
  onAddGuard: () => void
  onRemoveGuard: (tag: string) => void
  onSaveGenes: () => void
}>()

const dialogVisible = defineModel<boolean>('dialogVisible', { required: true })
const editDialogVisible = defineModel<boolean>('editDialogVisible', { required: true })
const editGenesVisible = defineModel<boolean>('editGenesVisible', { required: true })

const form = defineModel<{
  theme: string
  genre: string
  target_chapters: number
  special_requirements: string
  overwrite: boolean
}>('form', { required: true })

const editForm = defineModel<{
  title: string
  logline: string
  genre: string
  core_theme: string
  conflict: string
  protagonist_name: string
  protagonist_desire: string
  protagonist_flaw: string
  protagonist_edge: string
  protagonist_limit: string
}>('editForm', { required: true })

const editGenesForm = defineModel<{
  pleasure_mechanism: string
  protagonist_arc: string
  romance_weight: string
  pacing_baseline: string
  drift_guards: string[]
}>('editGenesForm', { required: true })

const newGuard = defineModel<string>('newGuard', { required: true })
</script>

<template>
  <el-dialog v-model="dialogVisible" title="生成作品大纲" width="640px" top="8vh">
    <el-form label-width="110px">
      <el-form-item label="主题/卖点" required>
        <el-input v-model="form.theme" placeholder="例如：现代都市中，女主通过电竞重建自我" />
      </el-form-item>
      <el-form-item label="题材">
        <el-input v-model="form.genre" placeholder="都市 / 玄幻 / 科幻 / 历史..." />
      </el-form-item>
      <el-form-item label="目标章数">
        <el-input-number v-model="form.target_chapters" :min="1" :max="3000" />
      </el-form-item>
      <el-form-item label="额外要求">
        <el-input v-model="form.special_requirements" type="textarea" :rows="5" resize="none" />
      </el-form-item>
      <el-form-item v-if="outline" label="更新方式">
        <el-radio-group v-model="form.overwrite">
          <el-radio :value="false">基于当前大纲补全（保留书名和主角）</el-radio>
          <el-radio :value="true">覆盖重生成</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button
        type="primary"
        :loading="submitting"
        :disabled="tasksRunning || submitting"
        @click="onSubmitOutline"
      >
        生成并保存
      </el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="editDialogVisible" title="编辑基础设定" width="720px" top="6vh">
    <el-form label-width="110px">
      <el-form-item label="作品名">
        <el-input v-model="editForm.title" placeholder="例如：《她与枪火》" />
      </el-form-item>
      <el-form-item label="一句话梗概">
        <el-input v-model="editForm.logline" />
      </el-form-item>
      <el-form-item label="题材定位">
        <el-input v-model="editForm.genre" />
      </el-form-item>
      <el-form-item label="核心主题">
        <el-input v-model="editForm.core_theme" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item label="核心冲突">
        <el-input v-model="editForm.conflict" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item label="主角名">
        <el-input v-model="editForm.protagonist_name" />
      </el-form-item>
      <el-form-item label="主角目标">
        <el-input v-model="editForm.protagonist_desire" />
      </el-form-item>
      <el-form-item label="主角缺陷">
        <el-input v-model="editForm.protagonist_flaw" />
      </el-form-item>
      <el-form-item label="主角优势">
        <el-input v-model="editForm.protagonist_edge" />
      </el-form-item>
      <el-form-item label="主角限制">
        <el-input v-model="editForm.protagonist_limit" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="onSaveOutlineBasics">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="editGenesVisible" title="编辑类型基因" width="600px" top="10vh">
    <el-form label-width="110px">
      <el-form-item label="爽点机制">
        <el-input v-model="editGenesForm.pleasure_mechanism" placeholder="如：金手指升级、打脸爽感" />
      </el-form-item>
      <el-form-item label="主角弧线">
        <el-input v-model="editGenesForm.protagonist_arc" placeholder="如：平民崛起、复仇救赎" />
      </el-form-item>
      <el-form-item label="感情线权重">
        <el-input v-model="editGenesForm.romance_weight" placeholder="如：单女主、轻感情重事业" />
      </el-form-item>
      <el-form-item label="节奏基调">
        <el-input v-model="editGenesForm.pacing_baseline" placeholder="如：快节奏爽文、慢热升级" />
      </el-form-item>
      <el-form-item label="防跑偏守护线">
        <div style="display: flex; gap: 10px; margin-bottom: 10px;">
          <el-input v-model="newGuard" placeholder="新增规则，如：绝不虐主、智商在线" @keyup.enter="onAddGuard" />
          <el-button type="primary" @click="onAddGuard">添加</el-button>
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
          <el-tag
            v-for="guard in editGenesForm.drift_guards"
            :key="guard"
            closable
            @close="onRemoveGuard(guard)"
          >
            {{ guard }}
          </el-tag>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="editGenesVisible = false">取消</el-button>
      <el-button type="primary" @click="onSaveGenes">保存</el-button>
    </template>
  </el-dialog>
</template>