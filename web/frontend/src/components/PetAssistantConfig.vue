<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { usePetStore } from '../stores/pet'
import { SHANSHAN_CONFIG_BLURB } from '../constants/shanshanCopy'
import { getConfig, listModels, updateConfig } from '../api'

const pet = usePetStore()
const expanded = ref(false)
const config = ref<any>({})
const libraryModels = ref<any[]>([])
const shanshanAvatar = new URL('../assets/pet/shanshan/ui/bubble_avatar.png', import.meta.url).href

const loadConfig = async () => {
  try {
    const { data } = await getConfig()
    config.value = data
  } catch (error: any) {
    ElMessage.error(error.message || '获取配置失败')
  }
}

const loadModels = async () => {
  try {
    const { data } = await listModels()
    libraryModels.value = data || []
  } catch (error: any) {
    ElMessage.error(error.message || '获取模型列表失败')
  }
}

const textModels = computed(() => {
  return libraryModels.value.filter((m: any) => m.type !== 'image')
})

const assistantModelRef = computed({
  get() {
    return config.value?.llm?.assistant?.model_ref || ''
  },
  async set(val: string) {
    try {
      if (!config.value.llm) {
        config.value.llm = {}
      }
      if (val) {
        config.value.llm.assistant = { model_ref: val }
      } else {
        if (config.value.llm.assistant) {
          delete config.value.llm.assistant
        }
      }
      await updateConfig(config.value)
      ElMessage.success('山山对话模型设置已更新')
      await loadConfig()
    } catch (error: any) {
      ElMessage.error(error.message || '保存设置失败')
    }
  }
})

onMounted(async () => {
  pet.loadSettings()
  await Promise.all([loadConfig(), loadModels()])
})

const handleLocateShanshan = async () => {
  try {
    if (!pet.settings.enabled) {
      await pet.updateSettings({ enabled: true })
    }
    if (window.electronAPI?.showPet) {
      await window.electronAPI.showPet()
      ElMessage.success('已唤醒桌面助手山山并居中定位')
    } else {
      window.dispatchEvent(new CustomEvent('open-shanshan'))
      ElMessage.success('已展开驻场助手山山')
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '定位山山失败')
  }
}

async function updateBoolean(key: 'enabled' | 'showOnStartup' | 'alwaysOnTop' | 'notifyOnTaskComplete' | 'notifyOnTaskError', value: boolean) {
  await pet.updateSettings({ [key]: value })
  if (key === 'enabled') {
    if (value) {
      if (window.electronAPI?.showPet) {
        await window.electronAPI.showPet()
      } else {
        window.dispatchEvent(new CustomEvent('open-shanshan'))
      }
    } else {
      await window.electronAPI?.hidePet?.()
    }
  }
}

const props = withDefaults(
  defineProps<{
    bare?: boolean
  }>(),
  {
    bare: false,
  },
)

async function updateSize(value: number) {
  await pet.updateSettings({ size: value })
}
</script>

<template>
  <section class="fold-card pet-config" :class="{ 'is-bare': bare }">
    <div v-if="!bare" class="fold-head" @click="expanded = !expanded">
      <div class="head-left">
        <span class="collapse-arrow" :class="{ open: expanded }">▶</span>
        <div>
          <h2>山山</h2>
          <p>{{ SHANSHAN_CONFIG_BLURB }}</p>
        </div>
      </div>
      <div class="title-action" @click.stop>
        <el-switch
          :model-value="pet.settings.enabled"
          active-text="启用"
          @change="(value: any) => updateBoolean('enabled', Boolean(value))"
        />
      </div>
    </div>
    
    <div v-show="bare || expanded" class="fold-body pet-config-body">
      <div v-if="bare" class="bare-pet-head">
        <div class="bare-pet-info">
          <img :src="shanshanAvatar" class="bare-pet-avatar" alt="山山" />
          <div class="bare-pet-meta">
            <div class="bare-pet-title-row">
              <strong>山山（驻场小编辑）</strong>
              <el-tag size="small" :type="pet.settings.enabled ? 'success' : 'info'" effect="plain">
                {{ pet.settings.enabled ? '运行中' : '未启用' }}
              </el-tag>
            </div>
            <span>{{ SHANSHAN_CONFIG_BLURB }}</span>
          </div>
        </div>
        <div class="bare-pet-actions">
          <el-button
            size="small"
            type="primary"
            plain
            class="locate-pet-btn"
            @click="handleLocateShanshan"
          >
            唤醒并定位
          </el-button>
          <el-switch
            :model-value="pet.settings.enabled"
            active-text="启用"
            @change="(value: any) => updateBoolean('enabled', Boolean(value))"
          />
        </div>
      </div>
      <div class="setting-row">
        <div>
          <strong>启动时显示</strong>
          <span>打开桌面端后自动显示山山。</span>
        </div>
        <el-switch
          :model-value="pet.settings.showOnStartup"
          @change="(value: any) => updateBoolean('showOnStartup', Boolean(value))"
        />
      </div>

      <div class="setting-row">
        <div>
          <strong>总在最前</strong>
          <span>让助手保持在其他窗口上方。</span>
        </div>
        <el-switch
          :model-value="pet.settings.alwaysOnTop"
          @change="(value: any) => updateBoolean('alwaysOnTop', Boolean(value))"
        />
      </div>

      <div class="setting-row">
        <div>
          <strong>任务提醒</strong>
          <span>任务完成或失败时允许山山切换状态并弹提示。</span>
        </div>
        <div class="notify-switches">
          <el-checkbox
            :model-value="pet.settings.notifyOnTaskComplete"
            @change="(value: any) => updateBoolean('notifyOnTaskComplete', Boolean(value))"
          >
            完成
          </el-checkbox>
          <el-checkbox
            :model-value="pet.settings.notifyOnTaskError"
            @change="(value: any) => updateBoolean('notifyOnTaskError', Boolean(value))"
          >
            失败
          </el-checkbox>
        </div>
      </div>

      <div class="setting-row">
        <div>
          <strong>对话大模型</strong>
          <span>设置山山对话所使用的大模型，留空则继承日常档。</span>
        </div>
        <el-select v-model="assistantModelRef" clearable placeholder="继承日常档" style="width: 180px">
          <el-option
            v-for="model in textModels"
            :key="model.id"
            :label="model.name || model.id"
            :value="model.id"
          />
        </el-select>
      </div>

      <div class="setting-row size-row">
        <div>
          <strong>显示尺寸</strong>
          <span>{{ pet.settings.size }} px</span>
        </div>
        <el-slider
          :model-value="pet.settings.size"
          :min="128"
          :max="260"
          :step="4"
          @change="(value: any) => updateSize(Number(value))"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.pet-config {
  margin-bottom: 12px;
}

.title-action {
  margin-right: 14px;
}

.pet-config-body {
  display: grid;
  gap: 0;
  padding: 0 14px 10px;
}

.setting-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  padding: 14px 0;
  border-top: 1px solid var(--color-border-subtle, #edf0f4);
}

.setting-row:first-child {
  border-top: 0;
}

.setting-row strong,
.setting-row span {
  display: block;
}

.setting-row strong {
  color: var(--color-text-strong, #1f2937);
  font-size: 13.5px;
  font-weight: 600;
}

.setting-row span {
  margin-top: 3px;
  color: var(--color-text-muted, #64748b);
  font-size: 12.5px;
  line-height: 1.45;
}

.size-row {
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 20px;
}

.notify-switches {
  display: flex;
  gap: 10px;
}

.bare-pet-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 12px;
  border-bottom: 1px dashed var(--color-border);
}

.bare-pet-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bare-pet-avatar {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
  border: 1px solid var(--color-border-subtle);
  background: var(--color-bg-base);
}

.bare-pet-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.bare-pet-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.bare-pet-title-row strong {
  font-size: 14px;
  color: var(--color-text-strong);
}

.bare-pet-meta span {
  font-size: 12px;
  color: var(--color-text-muted);
}

.bare-pet-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.locate-pet-btn {
  font-size: 12px;
  padding: 4px 10px;
}
</style>
