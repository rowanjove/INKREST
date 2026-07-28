import { ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  suggestCoverPrompt,
  generateCover,
  saveCover,
  listModels,
  apiErrorMessage,
} from '../api'
import type { Project } from '../stores/project'

type UseLibraryCoverOptions = {
  selectedProject: Ref<Project | null>
  coverTimestamps: Ref<Record<string, number>>
  refreshProjects: () => Promise<void>
}

export function useLibraryCover({ selectedProject, coverTimestamps, refreshProjects }: UseLibraryCoverOptions) {
  const coverManagerVisible = ref(false)
  const imageModels = ref<any[]>([])
  const selectedImageModel = ref('')
  const coverPrompt = ref('')
  const generatingPrompt = ref(false)
  const coverGenerating = ref(false)
  const generatedRawImage = ref('')

  const cropImageSrc = ref('')
  const cropperImg = ref<HTMLImageElement | null>(null)
  const scale = ref(1.0)
  const minScale = ref(0.1)
  const translateX = ref(0)
  const translateY = ref(0)
  const isDragging = ref(false)
  const dragStart = { x: 0, y: 0 }
  const savingCover = ref(false)
  const fileInputCover = ref<HTMLInputElement | null>(null)

  const openCoverManager = async () => {
    if (!selectedProject.value) return
    generatedRawImage.value = ''
    cropImageSrc.value = ''
    coverPrompt.value = ''
    selectedImageModel.value = ''

    try {
      const { data } = await listModels()
      imageModels.value = data.filter((m: any) => m.type === 'image')
      if (imageModels.value.length > 0) {
        selectedImageModel.value = imageModels.value[0].id
      }
    } catch (error) {
      console.error('拉取模型库失败', error)
    }

    coverManagerVisible.value = true
  }

  const handleSuggestCoverPrompt = async () => {
    if (!selectedProject.value) return
    generatingPrompt.value = true
    try {
      const { data } = await suggestCoverPrompt(selectedProject.value.id)
      coverPrompt.value = data.prompt
      ElMessage.success('画图提示词生成成功！')
    } catch (error: any) {
      ElMessage.error('提示词生成失败: ' + apiErrorMessage(error, '提示词生成失败'))
    } finally {
      generatingPrompt.value = false
    }
  }

  const handleGenerateCover = async () => {
    if (!selectedProject.value) return
    if (!selectedImageModel.value) {
      ElMessage.warning('请选择图像模型。若没有模型，请先去模型库配置。')
      return
    }
    if (!coverPrompt.value.trim()) {
      ElMessage.warning('画图提示词不能为空')
      return
    }
    coverGenerating.value = true
    try {
      const { data } = await generateCover(selectedProject.value.id, {
        model_id: selectedImageModel.value,
        prompt: coverPrompt.value,
      })
      generatedRawImage.value = data.image
      cropImageSrc.value = data.image
      ElMessage.success('封面图片生成成功！现在可以进行裁剪。')
    } catch (error: any) {
      ElMessage.error('封面生成失败: ' + apiErrorMessage(error, '封面生成失败'))
    } finally {
      coverGenerating.value = false
    }
  }

  const triggerCoverUpload = () => {
    fileInputCover.value?.click()
  }

  const handleCoverFileChange = (e: Event) => {
    const target = e.target as HTMLInputElement
    const file = target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      if (event.target?.result) {
        cropImageSrc.value = event.target.result as string
        generatedRawImage.value = ''
        ElMessage.success('本地图片加载成功！请在裁剪框中调整。')
      }
    }
    reader.readAsDataURL(file)
  }

  const initCropper = () => {
    if (!cropperImg.value) return
    const img = cropperImg.value
    const wRatio = 300 / img.naturalWidth
    const hRatio = 400 / img.naturalHeight
    const initialScale = Math.max(wRatio, hRatio)
    scale.value = initialScale
    minScale.value = initialScale * 0.4
    translateX.value = 0
    translateY.value = 0
  }

  const handleMouseDown = (e: MouseEvent) => {
    isDragging.value = true
    dragStart.x = e.clientX - translateX.value
    dragStart.y = e.clientY - translateY.value
  }

  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging.value) return
    translateX.value = e.clientX - dragStart.x
    translateY.value = e.clientY - dragStart.y
  }

  const handleMouseUp = () => {
    isDragging.value = false
  }

  const handleTouchStart = (e: TouchEvent) => {
    if (e.touches.length !== 1) return
    isDragging.value = true
    dragStart.x = e.touches[0].clientX - translateX.value
    dragStart.y = e.touches[0].clientY - translateY.value
  }

  const handleTouchMove = (e: TouchEvent) => {
    if (!isDragging.value || e.touches.length !== 1) return
    translateX.value = e.touches[0].clientX - dragStart.x
    translateY.value = e.touches[0].clientY - dragStart.y
  }

  const handleSaveCover = async () => {
    if (!selectedProject.value) return
    if (!cropImageSrc.value) {
      ElMessage.warning('没有可裁剪的图片')
      return
    }

    savingCover.value = true
    try {
      const croppedBase64 = await new Promise<string>((resolve, reject) => {
        if (!cropperImg.value) return reject('No image')
        const img = cropperImg.value
        const canvas = document.createElement('canvas')
        canvas.width = 600
        canvas.height = 800
        const ctx = canvas.getContext('2d')
        if (!ctx) return reject('No canvas context')

        ctx.fillStyle = 'var(--color-bg-surface)'
        ctx.fillRect(0, 0, 600, 800)

        const factor = 600 / 300
        ctx.save()
        ctx.translate(300 + translateX.value * factor, 400 + translateY.value * factor)
        ctx.scale(scale.value * factor, scale.value * factor)
        ctx.drawImage(img, -img.naturalWidth / 2, -img.naturalHeight / 2)
        ctx.restore()

        resolve(canvas.toDataURL('image/jpeg', 0.9))
      })

      await saveCover(selectedProject.value.id, croppedBase64)
      coverTimestamps.value[selectedProject.value.id] = Date.now()
      selectedProject.value.has_cover = true
      await refreshProjects()
      ElMessage.success('封面图片已成功裁剪并保存！')
      coverManagerVisible.value = false
    } catch (error: any) {
      ElMessage.error('保存封面失败: ' + apiErrorMessage(error, '保存封面失败'))
    } finally {
      savingCover.value = false
    }
  }

  return {
    coverManagerVisible,
    imageModels,
    selectedImageModel,
    coverPrompt,
    generatingPrompt,
    coverGenerating,
    cropImageSrc,
    cropperImg,
    scale,
    minScale,
    translateX,
    translateY,
    savingCover,
    fileInputCover,
    openCoverManager,
    handleSuggestCoverPrompt,
    handleGenerateCover,
    triggerCoverUpload,
    handleCoverFileChange,
    initCropper,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handleTouchStart,
    handleTouchMove,
    handleSaveCover,
  }
}