<script setup lang="ts">
import { Document, Download, Plus, Upload } from '@element-plus/icons-vue'
import type { Project } from '../../stores/project'
import { channelLabel, formatDate, formatWords, getCoverClass } from '../../utils/libraryFormatters'

const detailsVisible = defineModel<boolean>('detailsVisible', { required: true })
const rewriteVisible = defineModel<boolean>('rewriteVisible', { required: true })
const coverManagerVisible = defineModel<boolean>('coverManagerVisible', { required: true })

defineProps<{
  selectedProject: Project | null
  exportingZip: boolean
  rewriteLoading: boolean
  imageModels: any[]
  generatingPrompt: boolean
  coverGenerating: boolean
  cropImageSrc: string
  minScale: number
  translateX: number
  translateY: number
  savingCover: boolean
  getCoverUrl: (pid: string) => string
  onExportZip: (pid: string) => void
  onOpenCoverManager: () => void
  onCopyDescription: (text?: string) => void
  onOpenDescriptionRewriter: () => void
  onRewrite: () => void
  onApplyDescription: () => void
  onSuggestCoverPrompt: () => void
  onGenerateCover: () => void
  onTriggerCoverUpload: () => void
  onCoverFileChange: (e: Event) => void
  onInitCropper: () => void
  onMouseDown: (e: MouseEvent) => void
  onMouseMove: (e: MouseEvent) => void
  onMouseUp: () => void
  onTouchStart: (e: TouchEvent) => void
  onTouchMove: (e: TouchEvent) => void
  onSaveCover: () => void
}>()

const rewriteStyleModel = defineModel<string>('rewriteStyle', { required: true })
const userPreferenceModel = defineModel<string>('userPreference', { required: true })
const rewrittenDescModel = defineModel<string>('rewrittenDesc', { required: true })
const selectedImageModelModel = defineModel<string>('selectedImageModel', { required: true })
const coverPromptModel = defineModel<string>('coverPrompt', { required: true })
const scaleModel = defineModel<number>('scale', { required: true })

const cropperImgModel = defineModel<HTMLImageElement | null>('cropperImg', { required: true })
const fileInputCoverModel = defineModel<HTMLInputElement | null>('fileInputCover', { required: true })

const bindCropperImg = (el: unknown) => {
  cropperImgModel.value = el as HTMLImageElement | null
}

const bindFileInputCover = (el: unknown) => {
  fileInputCoverModel.value = el as HTMLInputElement | null
}
</script>

<template>
  <el-dialog
    v-model="detailsVisible"
    :title="selectedProject?.name || '书籍详情'"
    width="560px"
    destroy-on-close
    align-center
  >
    <div v-if="selectedProject" class="book-details-content">
      <div
        class="details-cover-preview"
        :class="getCoverClass(selectedProject.channel)"
        :style="selectedProject.has_cover ? { background: 'linear-gradient(to bottom, rgba(0, 0, 0, 0.3), rgba(0, 0, 0, 0.45)), url(' + getCoverUrl(selectedProject.id) + ') center/cover no-repeat' } : {}"
      >
        <div class="preview-design">
          <span v-if="selectedProject.genre" class="preview-genre">{{ selectedProject.genre }}</span>
          <h3 class="preview-title">{{ selectedProject.name }}</h3>
        </div>
        <el-button
          type="warning"
          size="small"
          :icon="Plus"
          style="position: absolute; right: 16px; bottom: 16px; z-index: 10;"
          @click="onOpenCoverManager"
        >
          更换封面
        </el-button>
      </div>

      <div class="details-info-grid">
        <div class="info-item full-width">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <span class="info-label">作品简介</span>
            <div style="display: flex; gap: 8px;">
              <el-button size="small" type="primary" link @click="onCopyDescription()">复制简介</el-button>
              <el-button size="small" type="warning" link @click="onOpenDescriptionRewriter">AI 重写</el-button>
            </div>
          </div>
          <p class="info-value desc-text">{{ selectedProject.description || '暂无简介' }}</p>
        </div>
        <div class="info-item">
          <span class="info-label">作品题材</span>
          <span class="info-value">{{ selectedProject.genre || '未设置' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">频道/受众</span>
          <span class="info-value">{{ channelLabel(selectedProject.channel) || '通用' }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">已生成章节</span>
          <span class="info-value">{{ selectedProject.chapter_count || 0 }} 章 / 目标 {{ selectedProject.target_chapters || '-' }} 章</span>
        </div>
        <div class="info-item">
          <span class="info-label">总字数</span>
          <span class="info-value">{{ formatWords(selectedProject.total_words) }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">创建时间</span>
          <span class="info-value">{{ formatDate(selectedProject.created_at) }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">上次更新</span>
          <span class="info-value">{{ formatDate(selectedProject.updated_at) }}</span>
        </div>
      </div>

      <div class="details-actions">
        <el-button
          type="primary"
          :icon="Download"
          :loading="exportingZip"
          @click="onExportZip(selectedProject.id)"
        >
          导出完整项目包 (.zip)
        </el-button>
      </div>
    </div>
  </el-dialog>

  <el-dialog
    v-model="rewriteVisible"
    title="AI 重写小说简介"
    width="600px"
    append-to-body
    align-center
  >
    <div v-if="selectedProject" style="display: flex; flex-direction: column; gap: 16px;">
      <div>
        <span style="font-weight: 600; font-size: 13.5px; color: var(--color-text-muted); display: block; margin-bottom: 8px;">原简介</span>
        <el-input
          v-model="selectedProject.description"
          type="textarea"
          rows="3"
          placeholder="当前简介内容"
          disabled
        />
      </div>

      <div style="display: flex; gap: 20px; align-items: center;">
        <span style="font-weight: 600; font-size: 13.5px; color: var(--color-text-muted); width: 70px;">重写风格:</span>
        <el-radio-group v-model="rewriteStyleModel">
          <el-radio value="爽文吸睛">爽文吸睛</el-radio>
          <el-radio value="悬疑勾人">悬疑勾人</el-radio>
          <el-radio value="宏大叙事">宏大叙事</el-radio>
          <el-radio value="轻松搞笑">轻松搞笑</el-radio>
        </el-radio-group>
      </div>

      <div>
        <span style="font-weight: 600; font-size: 13.5px; color: var(--color-text-muted); display: block; margin-bottom: 8px;">修改偏好 (例如：带有一点吐槽元素、强调男主心路历程)</span>
        <el-input
          v-model="userPreferenceModel"
          placeholder="可选，请输入微调指令"
        />
      </div>

      <div style="text-align: right;">
        <el-button type="warning" :loading="rewriteLoading" @click="onRewrite">
          AI 一键重写
        </el-button>
      </div>

      <div v-if="rewrittenDescModel">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span style="font-weight: 700; font-size: 14px; color: var(--color-text-strong);">AI 重写结果 (番茄平台常规字数长度)</span>
          <div style="display: flex; gap: 8px;">
            <el-button size="small" type="primary" plain @click="onCopyDescription(rewrittenDescModel)">复制</el-button>
            <el-button size="small" type="success" @click="onApplyDescription">保存并应用</el-button>
          </div>
        </div>
        <el-input
          v-model="rewrittenDescModel"
          type="textarea"
          rows="6"
          placeholder="重写后的内容将在此展示"
        />
      </div>
    </div>
  </el-dialog>

  <el-dialog
    v-model="coverManagerVisible"
    title="封面管理与裁剪"
    width="680px"
    append-to-body
    align-center
  >
    <div v-if="selectedProject" style="display: grid; grid-template-columns: 320px 1fr; gap: 24px;">
      <div style="display: flex; flex-direction: column; align-items: center; gap: 12px;">
        <span style="font-weight: 700; font-size: 14px; color: var(--color-text-strong);">3:4 封面裁剪预览</span>

        <div
          v-if="cropImageSrc"
          class="crop-viewport"
          style="width: 270px; height: 360px; overflow: hidden; position: relative; border: 2px solid var(--color-border); border-radius: 8px; background: var(--color-text-strong); cursor: move; box-shadow: 0 4px 12px rgba(0,0,0,0.15);"
          @mousedown="onMouseDown"
          @mousemove="onMouseMove"
          @mouseup="onMouseUp"
          @mouseleave="onMouseUp"
          @touchstart="onTouchStart"
          @touchmove="onTouchMove"
          @touchend="onMouseUp"
        >
          <img
            :src="cropImageSrc"
            :ref="bindCropperImg"
            :style="{
              position: 'absolute',
              left: '50%',
              top: '50%',
              width: 'auto',
              height: 'auto',
              maxWidth: 'none',
              transform: 'translate(-50%, -50%) translate(' + translateX + 'px, ' + translateY + 'px) scale(' + scaleModel + ')',
              pointerEvents: 'none',
            }"
            @load="onInitCropper"
          />
        </div>
        <div
          v-else
          style="width: 270px; height: 360px; display: flex; flex-direction: column; align-items: center; justify-content: center; background: var(--color-bg-surface-muted); border: 2px dashed var(--color-border); border-radius: 8px; color: var(--color-text-subtle); text-align: center; padding: 16px;"
        >
          <el-icon :size="40"><Document /></el-icon>
          <span style="margin-top: 12px; font-size: 13px;">请选择本地图片或使用图像大模型生成，随后在此裁剪。</span>
        </div>

        <div v-if="cropImageSrc" style="width: 270px; display: flex; align-items: center; gap: 10px;">
          <span style="font-size: 12px; color: var(--color-text-muted);">缩放</span>
          <el-slider v-model="scaleModel" :min="minScale" :max="scaleModel * 4" :step="0.01" :show-tooltip="false" style="flex: 1;" />
        </div>

        <el-button
          v-if="cropImageSrc"
          type="primary"
          :loading="savingCover"
          style="width: 270px; margin-top: 8px;"
          @click="onSaveCover"
        >
          确认并保存封面
        </el-button>
      </div>

      <div style="display: flex; flex-direction: column; gap: 16px; border-left: 1px solid var(--color-border); padding-left: 20px;">
        <div>
          <span style="font-weight: 700; font-size: 14px; color: var(--color-text-strong); display: block; margin-bottom: 12px;">方式一：AI 图像大模型生成</span>

          <div style="margin-bottom: 12px;">
            <span style="font-size: 13px; color: var(--color-text-muted); display: block; margin-bottom: 6px;">选择已配置的图像模型</span>
            <el-select v-model="selectedImageModelModel" placeholder="选择已配置的图像模型" style="width: 100%;">
              <el-option
                v-for="model in imageModels"
                :key="model.id"
                :label="model.name || model.id"
                :value="model.id"
              />
            </el-select>
            <small v-if="imageModels.length === 0" style="color: var(--color-danger); display: block; margin-top: 4px;">
              模型库内未检测到图像模型，请先去“模型库”中添加配置。
            </small>
          </div>

          <div style="margin-bottom: 12px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
              <span style="font-size: 13px; color: var(--color-text-muted);">画图提示词 (Prompt)</span>
              <el-button size="small" type="warning" plain :loading="generatingPrompt" @click="onSuggestCoverPrompt">
                自动推荐提示词
              </el-button>
            </div>
            <el-input
              v-model="coverPromptModel"
              type="textarea"
              rows="4"
              placeholder="例如：中国水墨画风格，气势磅礴，一位白衣剑仙立于云巅之上..."
            />
          </div>

          <el-button
            type="warning"
            :loading="coverGenerating"
            :disabled="imageModels.length === 0 || !coverPromptModel.trim()"
            style="width: 100%;"
            @click="onGenerateCover"
          >
            生成封面原图
          </el-button>
        </div>

        <div style="border-top: 1px dashed var(--color-border); padding-top: 16px; margin-top: 8px;">
          <span style="font-weight: 700; font-size: 14px; color: var(--color-text-strong); display: block; margin-bottom: 12px;">方式二：本地文件上传</span>
          <el-button type="info" plain :icon="Upload" style="width: 100%;" @click="onTriggerCoverUpload">
            上传本地图片
          </el-button>
          <input
            :ref="bindFileInputCover"
            type="file"
            accept="image/*"
            style="display: none"
            @change="onCoverFileChange"
          />
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<style scoped>
.book-details-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.details-cover-preview {
  height: 120px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  position: relative;
  overflow: hidden;
  box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.15);
  background:
    linear-gradient(to bottom, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0) 36%),
    radial-gradient(circle at 78% 18%, rgba(255, 255, 255, 0.22), transparent 18%),
    linear-gradient(135deg, var(--cover-start), var(--cover-mid) 52%, var(--cover-end));
}

.cover-general {
  --cover-start: #3f7f75;
  --cover-mid: #73a88b;
  --cover-end: #d7be84;
}

.cover-male {
  --cover-start: #425f83;
  --cover-mid: #6f89ad;
  --cover-end: #d5c095;
}

.cover-female {
  --cover-start: #b86978;
  --cover-mid: #d89483;
  --cover-end: #ead19a;
}

.cover-custom {
  --cover-start: #76648d;
  --cover-mid: #9f8dae;
  --cover-end: #dcc28d;
}

.preview-design {
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--color-bg-surface);
}

.preview-genre {
  align-self: flex-start;
  font-size: 10px;
  background: rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 3px;
  padding: 2px 5px;
  font-weight: 700;
}

.preview-title {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.25);
}

.details-info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px 20px;
  background: var(--color-bg-surface-muted);
  padding: 18px;
  border-radius: 8px;
  border: 1px solid #eef2f6;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item.full-width {
  grid-column: span 2;
  border-bottom: 1px solid #eef2f6;
  padding-bottom: 12px;
}

.info-label {
  font-size: 12.5px;
  color: var(--color-text-muted);
  font-weight: 600;
}

.info-value {
  font-size: 14px;
  color: #1f2937;
  font-weight: 600;
}

.info-value.desc-text {
  font-size: 13.5px;
  color: #4b5563;
  line-height: 1.5;
  font-weight: 400;
  margin: 0;
}

.details-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}
</style>