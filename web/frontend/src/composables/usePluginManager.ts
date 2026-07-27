import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listPlugins,
  listUntrustedPlugins,
  trustPlugin,
  togglePlugin,
  updatePluginConfig,
  reloadPlugins,
  installPluginZip,
  deletePlugin,
} from '../api'
import {
  getTypeLabel,
  hasSchemaForm,
  pluginTypes,
  type PluginInfo,
} from '../utils/pluginManagerConfig'

export function usePluginManager() {
  const loading = ref(false)
  const pluginsList = ref<PluginInfo[]>([])
  const untrustedPlugins = ref<string[]>([])
  const searchQuery = ref('')
  const selectedType = ref('')
  const selectedStatus = ref('')

  const detailDialogVisible = ref(false)
  const configDialogVisible = ref(false)
  const installDialogVisible = ref(false)
  const selectedPlugin = ref<PluginInfo | null>(null)
  const configForm = ref<Record<string, any>>({})
  const configJsonMode = ref(false)
  const configJsonText = ref('')
  const installUploading = ref(false)
  const installDragOver = ref(false)
  const installFile = ref<File | null>(null)
  const helpDialogVisible = ref(false)
  const trustDialogVisible = ref(false)
  const trustTarget = ref<PluginInfo | null>(null)
  const trustAcknowledged = ref(false)
  const trustLoading = ref(false)

  const fetchPlugins = async () => {
    loading.value = true
    try {
      const [pluginsRes, untrustedRes] = await Promise.all([listPlugins(), listUntrustedPlugins()])
      pluginsList.value = pluginsRes.data || []
      untrustedPlugins.value = untrustedRes.data?.plugins || []
    } catch (error: any) {
      ElMessage.error('获取插件列表失败: ' + (error.response?.data?.detail || error.message))
    } finally {
      loading.value = false
    }
  }

  const handleTrust = (target: string | PluginInfo) => {
    const plugin =
      typeof target === 'string'
        ? pluginsList.value.find((item) => item.name === target)
        : target
    if (!plugin) {
      ElMessage.warning('插件信息已变化，请先重新扫描。')
      return
    }
    trustTarget.value = plugin
    trustAcknowledged.value = false
    trustDialogVisible.value = true
  }

  const confirmTrust = async () => {
    const plugin = trustTarget.value
    if (!plugin || !trustAcknowledged.value) return
    trustLoading.value = true
    try {
      await trustPlugin(
        plugin.name,
        plugin.digest,
        plugin.effective_capabilities,
      )
      trustDialogVisible.value = false
      ElMessage.success(`${plugin.display_name} 已建立信任；需要时可单独启用。`)
      await fetchPlugins()
    } catch (error: any) {
      const data = error.response?.data
      ElMessage.error('信任插件失败: ' + (data?.message || data?.detail || error.message))
      await fetchPlugins()
    } finally {
      trustLoading.value = false
    }
  }

  const handleScan = async () => {
    loading.value = true
    try {
      const res = await reloadPlugins()
      ElMessage.success(`重新扫描成功，共加载 ${res.data?.plugins_loaded || 0} 个插件`)
      await fetchPlugins()
    } catch (error: any) {
      ElMessage.error('扫描插件失败: ' + (error.response?.data?.detail || error.message))
    } finally {
      loading.value = false
    }
  }

  const handleToggle = async (plugin: PluginInfo) => {
    const target = !plugin.enabled
    if (target && plugin.source === 'local' && !plugin.trusted) {
      handleTrust(plugin)
      return
    }
    try {
      const res = await togglePlugin(plugin.name, target)
      plugin.enabled = res.data.enabled
      ElMessage.success(`${plugin.display_name} 已${plugin.enabled ? '启用' : '禁用'}`)
      await fetchPlugins()
    } catch (error: any) {
      const data = error.response?.data
      if (data?.code === 'plugin_trust_required') {
        handleTrust(plugin)
        return
      }
      ElMessage.error('切换插件状态失败: ' + (data?.message || data?.detail || error.message))
    }
  }

  const openInstallDialog = () => {
    installFile.value = null
    installDragOver.value = false
    installDialogVisible.value = true
  }

  const setInstallFile = (file: File | null) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.zip')) {
      ElMessage.warning('请选择 .zip 插件包')
      return
    }
    installFile.value = file
  }

  const onInstallDrop = (e: DragEvent) => {
    installDragOver.value = false
    e.preventDefault()
    const file = e.dataTransfer?.files?.[0]
    if (file) setInstallFile(file)
  }

  const onInstallFileChange = (e: Event) => {
    const input = e.target as HTMLInputElement
    const file = input.files?.[0]
    if (file) setInstallFile(file)
    input.value = ''
  }

  const submitInstall = async () => {
    if (!installFile.value) {
      ElMessage.warning('请先选择或拖入 .zip 文件')
      return
    }
    installUploading.value = true
    try {
      const res = await installPluginZip(installFile.value)
      ElMessage.success(res.data?.message || '插件安装成功')
      installDialogVisible.value = false
      installFile.value = null
      await fetchPlugins()
    } catch (error: any) {
      ElMessage.error('安装失败: ' + (error.response?.data?.detail || error.message))
    } finally {
      installUploading.value = false
    }
  }

  const handleDelete = async (plugin: PluginInfo) => {
    try {
      await ElMessageBox.confirm(
        `将删除插件「${plugin.display_name}」及其本地文件，此操作不可恢复。`,
        '删除插件',
        { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
      )
      await deletePlugin(plugin.name)
      ElMessage.success(`${plugin.display_name} 已删除`)
      await fetchPlugins()
    } catch (error: any) {
      if (error !== 'cancel') {
        ElMessage.error('删除失败: ' + (error.response?.data?.detail || error.message))
      }
    }
  }

  const showDetail = (plugin: PluginInfo) => {
    selectedPlugin.value = plugin
    detailDialogVisible.value = true
  }

  const showConfig = (plugin: PluginInfo) => {
    selectedPlugin.value = plugin
    configForm.value = JSON.parse(JSON.stringify(plugin.config || {}))
    configJsonMode.value = !hasSchemaForm(plugin)
    configJsonText.value = JSON.stringify(configForm.value, null, 2)

    const properties = plugin.config_schema?.properties || {}
    for (const key in properties) {
      if (configForm.value[key] === undefined || configForm.value[key] === null) {
        if (properties[key].default !== undefined) {
          configForm.value[key] = properties[key].default
        } else if (properties[key].type === 'boolean') {
          configForm.value[key] = false
        } else if (properties[key].type === 'array') {
          configForm.value[key] = []
        } else {
          configForm.value[key] = ''
        }
      }
    }

    configDialogVisible.value = true
  }

  const saveConfig = async () => {
    if (!selectedPlugin.value) return
    let payload = configForm.value
    if (configJsonMode.value) {
      try {
        payload = JSON.parse(configJsonText.value || '{}')
      } catch {
        ElMessage.error('JSON 格式无效，请检查后再保存')
        return
      }
    }
    try {
      const res = await updatePluginConfig(selectedPlugin.value.name, payload)
      selectedPlugin.value.config = res.data.config
      ElMessage.success(`${selectedPlugin.value.display_name} 配置更新成功`)
      configDialogVisible.value = false
      await fetchPlugins()
    } catch (error: any) {
      ElMessage.error('保存配置失败: ' + (error.response?.data?.detail || error.message))
    }
  }

  const filteredPlugins = computed(() => {
    return pluginsList.value.filter((p) => {
      const matchesSearch =
        p.name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
        p.display_name.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
        p.description.toLowerCase().includes(searchQuery.value.toLowerCase())
      const matchesType = !selectedType.value || p.plugin_type === selectedType.value
      const matchesStatus =
        !selectedStatus.value ||
        (selectedStatus.value === 'active' && p.enabled) ||
        (selectedStatus.value === 'inactive' && !p.enabled)
      return matchesSearch && matchesType && matchesStatus
    })
  })

  const totalCount = computed(() => pluginsList.value.length)
  const activeCount = computed(() => pluginsList.value.filter((p) => p.enabled).length)

  onMounted(() => {
    fetchPlugins()
  })

  return {
    loading,
    pluginsList,
    untrustedPlugins,
    searchQuery,
    selectedType,
    selectedStatus,
    pluginTypes,
    detailDialogVisible,
    configDialogVisible,
    installDialogVisible,
    selectedPlugin,
    configForm,
    configJsonMode,
    configJsonText,
    installUploading,
    installDragOver,
    installFile,
    helpDialogVisible,
    trustDialogVisible,
    trustTarget,
    trustAcknowledged,
    trustLoading,
    filteredPlugins,
    totalCount,
    activeCount,
    fetchPlugins,
    handleTrust,
    confirmTrust,
    handleScan,
    handleToggle,
    openInstallDialog,
    onInstallDrop,
    onInstallFileChange,
    submitInstall,
    handleDelete,
    showDetail,
    showConfig,
    saveConfig,
    getTypeLabel,
  }
}
