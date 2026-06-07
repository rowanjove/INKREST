import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import {
  createAsset,
  generateAsset,
  getAsset,
  listAssets,
  updateAsset,
  importToTerminology,
  deleteAsset,
  apiErrorMessage,
} from '../api'
import {
  assetNames,
  assetMeta,
  assetTypeOptions,
  type AssetItem,
  type AssetTypeKey,
  type AssetTypeOption,
} from '../utils/assetEditorConfig'

export function useAssetEditor() {
  const assets = ref<AssetItem[]>([])
  const currentAsset = ref<{ name: string; label?: string; path: string; content: string } | null>(null)
  const editContent = ref('')
  const showAssetSource = ref(false)
  const saving = ref(false)
  const loading = ref(false)
  const loadError = ref('')
  const createDialogVisible = ref(false)
  const generateDialogVisible = ref(false)
  const creating = ref(false)
  const generating = ref(false)

  const createForm = ref({
    name: '',
    label: '',
    extension: 'md',
    content: '',
  })

  const generateForm = ref({
    name: 'generated_asset',
    label: '',
    assetTypeKey: 'character_cards' as AssetTypeKey,
    count: 3,
    attributesText: '',
    parameters: {} as Record<string, string>,
    instructions: '',
  })

  const addTermDialogOpen = ref(false)
  const addTermForm = ref({
    name: '',
    description: '',
  })

  const selectedCustomAssets = ref<string[]>([])

  const selectedAssetType = computed(() =>
    assetTypeOptions.find((item) => item.key === generateForm.value.assetTypeKey) || assetTypeOptions[0]
  )

  const currentTitle = computed(() => {
    if (!currentAsset.value) return '选择资产'
    return currentAsset.value.label || assetNames[currentAsset.value.name] || currentAsset.value.name
  })

  const groupedAssets = computed(() => {
    const groups: Record<string, AssetItem[]> = {
      人物资产: [],
      设定资产: [],
      写作资产: [],
      自定义资产: [],
    }
    for (const asset of assets.value) {
      const group = assetMeta[asset.name]?.group || '自定义资产'
      groups[group].push(asset)
    }
    return Object.entries(groups)
      .map(([name, items]) => ({ name, items }))
      .filter((group) => group.items.length)
  })

  const currentMeta = computed(() => {
    if (!currentAsset.value) return null
    return assetMeta[currentAsset.value.name] || {
      group: '自定义资产',
      icon: Document,
      tone: 'gray',
      description: '项目专属补充素材，可作为章节生成参考。',
    }
  })

  const isMarkdownAsset = computed(() => {
    if (!currentAsset.value) return false
    return currentAsset.value.path.endsWith('.md')
  })

  const supportsAssetSource = computed(() => {
    return currentAsset.value?.name === 'character_cards' || isMarkdownAsset.value
  })

  const contentBlocks = computed(() => {
    const text = editContent.value || ''
    const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
    return lines
      .filter((line) => /^#{1,3}\s+/.test(line) || /^[\w\u4e00-\u9fa5_-]+:/.test(line) || /^-\s+/.test(line))
      .slice(0, 12)
      .map((line) => line.replace(/^#{1,3}\s+/, '').replace(/^-\s+/, ''))
  })

  const isAllCustomSelected = computed(() => {
    const customItems = assets.value.filter((a) => a.custom)
    if (customItems.length === 0) return false
    return customItems.every((a) => selectedCustomAssets.value.includes(a.name))
  })

  const isCustomIndeterminate = computed(() => {
    const customItems = assets.value.filter((a) => a.custom)
    if (customItems.length === 0) return false
    const selectedCount = customItems.filter((a) => selectedCustomAssets.value.includes(a.name)).length
    return selectedCount > 0 && selectedCount < customItems.length
  })

  const loadAsset = async (name: string) => {
    loading.value = true
    try {
      loadError.value = ''
      const { data } = await getAsset(name)
      currentAsset.value = data
      editContent.value = data.content
      showAssetSource.value = false
    } catch (error: any) {
      loadError.value = apiErrorMessage(error, '资产加载失败')
    } finally {
      loading.value = false
    }
  }

  const loadAssets = async () => {
    loading.value = true
    try {
      loadError.value = ''
      const { data } = await listAssets()
      const filtered = (data || []).filter(
        (a: AssetItem) => a.name !== 'style_guide' && a.name !== 'rules' && a.name !== 'sensitive_words'
      )
      assets.value = filtered
      if (!currentAsset.value && filtered.length > 0) {
        await loadAsset(filtered[0].name)
      }
    } catch (error: any) {
      loadError.value = apiErrorMessage(error, '资产列表加载失败')
    } finally {
      loading.value = false
    }
  }

  const handleSave = async () => {
    if (!currentAsset.value) return
    saving.value = true
    try {
      await updateAsset(currentAsset.value.name, editContent.value)
      ElMessage.success('资产已保存')
      await loadAssets()
    } catch (error: any) {
      ElMessage.error(apiErrorMessage(error, '保存失败'))
    } finally {
      saving.value = false
    }
  }

  const openAddTermDialog = () => {
    addTermForm.value = {
      name: '',
      description: '',
    }
    addTermDialogOpen.value = true
  }

  const handleAddTerm = async () => {
    if (!addTermForm.value.name.trim()) {
      ElMessage.warning('请填写名词名称')
      return
    }
    if (!addTermForm.value.description.trim()) {
      ElMessage.warning('请填写名词解释')
      return
    }

    const currentContent = editContent.value || ''
    const suffix = currentContent.endsWith('\n') ? '' : '\n'
    const newTermText = `${suffix}- **${addTermForm.value.name.trim()}**：${addTermForm.value.description.trim()}\n`
    editContent.value = currentContent + newTermText

    addTermDialogOpen.value = false
    await handleSave()
  }

  const handleCreate = async () => {
    if (!createForm.value.name.trim()) {
      ElMessage.warning('请填写资产标识')
      return
    }
    creating.value = true
    try {
      await createAsset(createForm.value)
      ElMessage.success('资产已新增')
      createDialogVisible.value = false
      await loadAssets()
      await loadAsset(createForm.value.name)
    } catch (error: any) {
      ElMessage.error(apiErrorMessage(error, '新增失败'))
    } finally {
      creating.value = false
    }
  }

  const parseParameters = () => {
    return Object.fromEntries(
      Object.entries(generateForm.value.parameters)
        .map(([key, value]) => [key.trim(), String(value || '').trim()])
        .filter(([key, value]) => key && value)
    )
  }

  const applyAssetTypeDefaults = (option: AssetTypeOption, forceName = false) => {
    if (forceName || !generateForm.value.name || generateForm.value.name === 'generated_asset') {
      generateForm.value.name = option.defaultName
    }
    if (forceName || !generateForm.value.label) {
      generateForm.value.label = option.defaultLabel
    }
    generateForm.value.attributesText = option.defaultAttributes.join(',')
    generateForm.value.parameters = { ...option.defaultParameters }
  }

  const openGenerateDialog = () => {
    applyAssetTypeDefaults(selectedAssetType.value)
    generateDialogVisible.value = true
  }

  watch(
    () => generateForm.value.assetTypeKey,
    () => applyAssetTypeDefaults(selectedAssetType.value, true)
  )

  const handleGenerate = async () => {
    if (!generateForm.value.name.trim()) {
      ElMessage.warning('请填写保存标识')
      return
    }
    generating.value = true
    try {
      const { data } = await generateAsset({
        name: generateForm.value.name,
        label: generateForm.value.label,
        asset_type: selectedAssetType.value.label,
        count: generateForm.value.count,
        attributes: generateForm.value.attributesText.split(',').map((item) => item.trim()).filter(Boolean),
        parameters: parseParameters(),
        instructions: generateForm.value.instructions,
      })
      ElMessage.success('AI 素材已生成')
      generateDialogVisible.value = false
      await loadAssets()
      await loadAsset(data.name)
    } catch (error: any) {
      ElMessage.error(apiErrorMessage(error, 'AI 生成失败'))
    } finally {
      generating.value = false
    }
  }

  const handleToggleSelectAllCustom = (val: any) => {
    const customItems = assets.value.filter((a) => a.custom)
    if (val) {
      selectedCustomAssets.value = customItems.map((a) => a.name)
    } else {
      selectedCustomAssets.value = []
    }
  }

  const handleToggleSelectAsset = (name: string) => {
    const idx = selectedCustomAssets.value.indexOf(name)
    if (idx > -1) {
      selectedCustomAssets.value.splice(idx, 1)
    } else {
      selectedCustomAssets.value.push(name)
    }
  }

  const handleBulkImportToTerminology = async () => {
    if (selectedCustomAssets.value.length === 0) return
    try {
      await ElMessageBox.confirm(
        `确定要将选中的 ${selectedCustomAssets.value.length} 个自定义资产导入到“名词解释”中吗？`,
        '导入名词解释',
        { confirmButtonText: '确定', cancelButtonText: '取消', type: 'info' }
      )
      await importToTerminology({ names: selectedCustomAssets.value })
      ElMessage.success('导入成功！')
      selectedCustomAssets.value = []
      await loadAssets()
      await loadAsset('terminology')
    } catch (error: any) {
      if (error !== 'cancel') ElMessage.error(error.message || '导入失败')
    }
  }

  const handleBulkDelete = async () => {
    if (selectedCustomAssets.value.length === 0) return
    try {
      await ElMessageBox.confirm(
        `确定要删除选中的 ${selectedCustomAssets.value.length} 个自定义资产吗？该操作不可撤销。`,
        '批量删除资产',
        { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
      )
      loading.value = true
      for (const name of selectedCustomAssets.value) {
        await deleteAsset(name)
      }
      ElMessage.success('批量删除成功！')
      const deletedNames = [...selectedCustomAssets.value]
      selectedCustomAssets.value = []
      if (currentAsset.value && deletedNames.includes(currentAsset.value.name)) {
        currentAsset.value = null
      }
      await loadAssets()
    } catch (error: any) {
      if (error !== 'cancel') ElMessage.error(error.message || '删除失败')
    } finally {
      loading.value = false
    }
  }

  const handleContextCommand = async (command: string, asset: AssetItem) => {
    if (command === 'import_to_terminology') {
      let targetNames = [asset.name]
      if (selectedCustomAssets.value.includes(asset.name) && selectedCustomAssets.value.length > 0) {
        targetNames = [...selectedCustomAssets.value]
      }
      try {
        await importToTerminology({ names: targetNames })
        ElMessage.success('成功导入名词解释！')
        selectedCustomAssets.value = selectedCustomAssets.value.filter((name) => !targetNames.includes(name))
        await loadAssets()
        await loadAsset('terminology')
      } catch (error: any) {
        ElMessage.error(error.message || '导入失败')
      }
    } else if (command === 'delete_asset') {
      try {
        await ElMessageBox.confirm(
          `确定要删除自定义资产「${asset.label || asset.name}」吗？该操作不可撤销。`,
          '删除资产',
          { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
        )
        await deleteAsset(asset.name)
        ElMessage.success('资产已删除')
        selectedCustomAssets.value = selectedCustomAssets.value.filter((name) => name !== asset.name)
        if (currentAsset.value?.name === asset.name) {
          currentAsset.value = null
        }
        await loadAssets()
      } catch (error: any) {
        if (error !== 'cancel') ElMessage.error(error.message || '删除失败')
      }
    }
  }

  return {
    assets,
    currentAsset,
    editContent,
    showAssetSource,
    saving,
    loading,
    loadError,
    createDialogVisible,
    generateDialogVisible,
    creating,
    generating,
    createForm,
    generateForm,
    addTermDialogOpen,
    addTermForm,
    selectedCustomAssets,
    selectedAssetType,
    currentTitle,
    groupedAssets,
    currentMeta,
    isMarkdownAsset,
    supportsAssetSource,
    contentBlocks,
    isAllCustomSelected,
    isCustomIndeterminate,
    loadAsset,
    loadAssets,
    handleSave,
    openAddTermDialog,
    handleAddTerm,
    handleCreate,
    openGenerateDialog,
    handleGenerate,
    handleToggleSelectAllCustom,
    handleToggleSelectAsset,
    handleBulkImportToTerminology,
    handleBulkDelete,
    handleContextCommand,
  }
}