<script setup lang="ts">
import type { PluginInfo } from '../../utils/pluginManagerConfig'

const detailDialogVisible = defineModel<boolean>('detailDialogVisible', { required: true })
const configDialogVisible = defineModel<boolean>('configDialogVisible', { required: true })
const installDialogVisible = defineModel<boolean>('installDialogVisible', { required: true })
const configForm = defineModel<Record<string, any>>('configForm', { required: true })
const configJsonText = defineModel<string>('configJsonText', { required: true })
const installDragOver = defineModel<boolean>('installDragOver', { required: true })

defineProps<{
  selectedPlugin: PluginInfo | null
  configJsonMode: boolean
  installUploading: boolean
  installFile: File | null
  getTypeLabel: (typeVal: string) => string
  onInstallDrop: (e: DragEvent) => void
  onInstallFileChange: (e: Event) => void
  onSubmitInstall: () => void
  onSaveConfig: () => void
}>()
</script>

<template>
  <el-dialog v-model="detailDialogVisible" title="ℹ️ 插件详细信息" width="500px" align-center>
    <div v-if="selectedPlugin" class="plugin-detail-dialog-content">
      <div class="detail-row">
        <span class="detail-label">插件名称：</span>
        <span class="detail-value"><strong>{{ selectedPlugin.display_name }}</strong></span>
      </div>
      <div class="detail-row">
        <span class="detail-label">唯一标识：</span>
        <span class="detail-value"><code>{{ selectedPlugin.name }}</code></span>
      </div>
      <div class="detail-row">
        <span class="detail-label">版本：</span>
        <span class="detail-value">v{{ selectedPlugin.version }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">作者：</span>
        <span class="detail-value">{{ selectedPlugin.author || '未知' }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">安装来源：</span>
        <span class="detail-value">
          <el-tag :type="selectedPlugin.source === 'local' ? 'warning' : 'success'">
            {{ selectedPlugin.source }}
          </el-tag>
        </span>
      </div>
      <div class="detail-row">
        <span class="detail-label">扩展类型：</span>
        <span class="detail-value">{{ getTypeLabel(selectedPlugin.plugin_type) }}</span>
      </div>
      <div v-if="selectedPlugin.requires && selectedPlugin.requires.length > 0" class="detail-row">
        <span class="detail-label">依赖关系：</span>
        <span class="detail-value">
          <el-tag
            v-for="req in selectedPlugin.requires"
            :key="req"
            size="small"
            type="danger"
            style="margin-right: 5px;"
          >
            {{ req }}
          </el-tag>
        </span>
      </div>
      <div class="detail-row">
        <span class="detail-label">最小核心版本：</span>
        <span class="detail-value"><code>{{ selectedPlugin.min_core_version }}</code></span>
      </div>
      <div class="detail-desc-box">
        <strong>插件描述：</strong>
        <p>{{ selectedPlugin.description || '无。' }}</p>
      </div>
    </div>
    <template #footer>
      <el-button @click="detailDialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="installDialogVisible" title="载入插件" width="480px" align-center>
    <div
      class="install-dropzone"
      :class="{ 'is-dragover': installDragOver, 'has-file': !!installFile }"
      @dragover.prevent="installDragOver = true"
      @dragleave.prevent="installDragOver = false"
      @drop.prevent="onInstallDrop"
    >
      <p class="drop-title">将 .zip 插件包拖放到此处</p>
      <p class="drop-hint">根目录须包含 inkrest.plugin.json</p>
      <input
        id="plugin-zip-input"
        type="file"
        accept=".zip,application/zip"
        class="hidden-file-input"
        @change="onInstallFileChange"
      />
      <label for="plugin-zip-input" class="pick-file-btn">选择文件</label>
      <p v-if="installFile" class="picked-file">{{ installFile.name }}</p>
    </div>
    <template #footer>
      <el-button @click="installDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="installUploading" @click="onSubmitInstall">
        安装
      </el-button>
    </template>
  </el-dialog>

  <el-dialog
    v-model="configDialogVisible"
    :title="`⚙️ 配置 - ${selectedPlugin?.display_name}`"
    width="550px"
    align-center
  >
    <div v-if="selectedPlugin" class="plugin-config-form">
      <el-alert
        v-if="configJsonMode"
        type="info"
        :closable="false"
        show-icon
        title="该插件未提供 config_schema，可使用 JSON 编辑参数。"
        style="margin-bottom: 12px"
      />
      <el-input
        v-if="configJsonMode"
        v-model="configJsonText"
        type="textarea"
        :rows="12"
        placeholder='{"key": "value"}'
      />
      <el-form v-else label-position="top">
        <template v-for="(prop, key) in selectedPlugin.config_schema.properties" :key="key">
          <el-form-item :label="prop.title || key">
            <div v-if="prop.description" class="form-item-desc">{{ prop.description }}</div>

            <el-switch
              v-if="prop.type === 'boolean'"
              v-model="configForm[key]"
              active-color="#c66f4f"
            />

            <el-checkbox-group
              v-else-if="prop.type === 'array' && prop.items && prop.items.enum"
              v-model="configForm[key]"
            >
              <el-checkbox
                v-for="item in prop.items.enum"
                :key="item"
                :label="item"
                :value="item"
              />
            </el-checkbox-group>

            <el-select
              v-else-if="prop.type === 'string' && prop.enum"
              v-model="configForm[key]"
              style="width: 100%;"
            >
              <el-option
                v-for="item in prop.enum"
                :key="item"
                :label="item"
                :value="item"
              />
            </el-select>

            <el-input
              v-else
              v-model="configForm[key]"
              :type="prop.type === 'string' && prop.format === 'textarea' ? 'textarea' : 'text'"
              :rows="3"
              placeholder="请输入配置项值"
            />
          </el-form-item>
        </template>
      </el-form>
    </div>
    <template #footer>
      <el-button @click="configDialogVisible = false">取消</el-button>
      <el-button type="primary" @click="onSaveConfig">保存配置</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.install-dropzone {
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  padding: 32px 20px;
  text-align: center;
  transition: border-color 0.2s, background 0.2s;
}

.install-dropzone.is-dragover,
.install-dropzone.has-file {
  border-color: var(--primary);
  background: #fff6f2;
}

.drop-title {
  margin: 0 0 6px;
  font-weight: 700;
  color: #1f2937;
}

.drop-hint {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--text-muted);
}

.hidden-file-input {
  display: none;
}

.pick-file-btn {
  display: inline-block;
  padding: 8px 16px;
  background: var(--primary);
  color: var(--color-bg-surface);
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
}

.picked-file {
  margin-top: 12px;
  font-size: 13px;
  color: #374151;
  word-break: break-all;
}

.plugin-detail-dialog-content {
  display: grid;
  gap: 12px;
}

.detail-row {
  display: flex;
  font-size: 14.5px;
}

.detail-label {
  color: var(--text-muted);
  width: 110px;
  flex-shrink: 0;
}

.detail-value {
  color: var(--text-main);
  word-break: break-all;
}

.detail-desc-box {
  margin-top: 14px;
  padding: 12px;
  background: var(--color-bg-surface-muted);
  border-radius: 8px;
  border: 1px solid var(--border-light);
}

.detail-desc-box strong {
  display: block;
  font-size: 13px;
  color: var(--text-main);
  margin-bottom: 6px;
}

.detail-desc-box p {
  margin: 0;
  font-size: 13.5px;
  color: var(--text-muted);
  line-height: 1.6;
}

.form-item-desc {
  font-size: 12.5px;
  color: var(--text-muted);
  line-height: 1.4;
  margin-bottom: 8px;
  width: 100%;
}
</style>