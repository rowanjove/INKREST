<script setup lang="ts">
import type { PluginInfo } from '../../utils/pluginManagerConfig'

const detailDialogVisible = defineModel<boolean>('detailDialogVisible', { required: true })
const configDialogVisible = defineModel<boolean>('configDialogVisible', { required: true })
const installDialogVisible = defineModel<boolean>('installDialogVisible', { required: true })
const trustDialogVisible = defineModel<boolean>('trustDialogVisible', { required: true })
const trustAcknowledged = defineModel<boolean>('trustAcknowledged', { required: true })
const configForm = defineModel<Record<string, any>>('configForm', { required: true })
const configJsonText = defineModel<string>('configJsonText', { required: true })
const installDragOver = defineModel<boolean>('installDragOver', { required: true })

defineProps<{
  selectedPlugin: PluginInfo | null
  configJsonMode: boolean
  installUploading: boolean
  installFile: File | null
  trustTarget: PluginInfo | null
  trustLoading: boolean
  getTypeLabel: (typeVal: string) => string
  onInstallDrop: (e: DragEvent) => void
  onInstallFileChange: (e: Event) => void
  onSubmitInstall: () => void
  onSaveConfig: () => void
  onConfirmTrust: () => void
}>()
</script>

<template>
  <el-dialog
    v-model="trustDialogVisible"
    title="检查插件权限"
    width="560px"
    align-center
    @closed="trustAcknowledged = false"
  >
    <div v-if="trustTarget" class="trust-dialog">
      <el-alert
        :title="trustTarget.requires_reauthorization ? '插件内容或权限已变化，需要重新授权' : '本地插件将在栖墨后端进程中运行代码'"
        type="warning"
        :closable="false"
        show-icon
      >
        {{ trustTarget.risk_summary }}
      </el-alert>

      <dl class="trust-facts">
        <div><dt>插件</dt><dd>{{ trustTarget.display_name }} · v{{ trustTarget.version }}</dd></div>
        <div><dt>来源</dt><dd>{{ trustTarget.origin }}</dd></div>
        <div><dt>作者</dt><dd>{{ trustTarget.author || '未声明' }}</dd></div>
        <div>
          <dt>权限模式</dt>
          <dd>
            {{
              trustTarget.capability_mode === 'legacy'
                ? '旧式插件（最高边界）'
                : trustTarget.capability_mode === 'explicit'
                  ? '清单已声明'
                  : '按插件类型推导'
            }}
          </dd>
        </div>
      </dl>

      <section class="permission-list">
        <h3>将授予的权限</h3>
        <article
          v-for="permission in trustTarget.capability_details"
          :key="permission.id"
        >
          <div>
            <strong>{{ permission.label }}</strong>
            <span :class="`risk-${permission.risk}`">{{ permission.risk }}</span>
          </div>
          <p>{{ permission.description }}</p>
        </article>
      </section>

      <div class="digest-row">
        <span>内容摘要 SHA-256</span>
        <code>{{ trustTarget.digest }}</code>
      </div>

      <el-checkbox v-model="trustAcknowledged" class="trust-check">
        我已核对来源、内容摘要与上述权限，并理解 Python 插件不受操作系统沙箱隔离。
      </el-checkbox>
    </div>
    <template #footer>
      <el-button @click="trustDialogVisible = false">取消</el-button>
      <el-button
        type="warning"
        :loading="trustLoading"
        :disabled="!trustAcknowledged"
        @click="onConfirmTrust"
      >
        仅建立信任
      </el-button>
    </template>
  </el-dialog>

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
      <div class="detail-row">
        <span class="detail-label">信任状态：</span>
        <span class="detail-value">
          {{ selectedPlugin.trusted ? '内容与权限已确认' : '尚未确认' }}
        </span>
      </div>
      <div class="detail-row">
        <span class="detail-label">内容摘要：</span>
        <span class="detail-value digest-value"><code>{{ selectedPlugin.digest }}</code></span>
      </div>
      <div class="detail-desc-box">
        <strong>有效权限：</strong>
        <p>{{ selectedPlugin.capability_details.map((item) => item.label).join('、') }}</p>
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
.trust-dialog {
  display: grid;
  gap: 16px;
}

.trust-facts {
  display: grid;
  gap: 7px;
  margin: 0;
}
.trust-facts > div { display: grid; grid-template-columns: 84px minmax(0, 1fr); gap: 10px; }
.trust-facts dt { color: var(--color-text-muted); font-size: 12px; }
.trust-facts dd { margin: 0; color: var(--color-text-strong); font-size: 12px; }

.permission-list {
  display: grid;
  gap: 7px;
}
.permission-list h3 { margin: 0 0 2px; color: var(--color-text-strong); font-size: 13px; }
.permission-list article {
  padding: 9px 11px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
}
.permission-list article > div { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.permission-list strong { color: var(--color-text-strong); font-size: 12px; }
.permission-list article span { font-size: 9px; font-weight: 800; text-transform: uppercase; }
.permission-list article p { margin: 3px 0 0; color: var(--color-text-muted); font-size: 11px; line-height: 1.45; }
.risk-low { color: var(--color-success); }
.risk-medium { color: var(--color-warning); }
.risk-high { color: var(--color-danger); }

.digest-row {
  display: grid;
  gap: 5px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--color-bg-surface-muted);
}
.digest-row span { color: var(--color-text-muted); font-size: 10px; }
.digest-row code,
.digest-value code { overflow-wrap: anywhere; color: var(--color-text-strong); font-size: 10px; }
.trust-check { align-items: flex-start; white-space: normal; }
.trust-check :deep(.el-checkbox__label) { color: var(--color-text); font-size: 11px; line-height: 1.5; white-space: normal; }

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
