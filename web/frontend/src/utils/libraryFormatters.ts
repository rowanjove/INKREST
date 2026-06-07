import type { Project } from '../stores/project'

export const channelLabel = (id?: string) => {
  if (!id) return ''
  const map: Record<string, string> = { general: '通用', male: '男频', female: '女频', custom: '自定' }
  return map[id] || ''
}

export const formatDate = (iso?: string) => {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString('zh-CN', { year: 'numeric', month: 'short', day: 'numeric' })
}

/** 书库封面：带年份的更新日期 */
export const formatCardDate = (iso?: string) => {
  if (!iso) return '暂无'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '暂无'
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
}

/** 书库封面左下角：时:分 */
export const formatCardTime = (iso?: string) => {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${h}:${min}`
}

export const lastEditIso = (project: Project) => project.activity_at || project.updated_at

export const lastEditLabel = (project: Project) => formatCardDate(lastEditIso(project))

export const lastEditTime = (project: Project) => formatCardTime(lastEditIso(project))

export const lastEditTitle = (project: Project) => {
  const date = lastEditLabel(project)
  const time = lastEditTime(project)
  if (date === '暂无') return '更新时间未知'
  return time ? `更新 ${date} ${time}` : `更新 ${date}`
}

export const getCoverClass = (channel?: string) => {
  if (channel === 'male') return 'cover-male'
  if (channel === 'female') return 'cover-female'
  if (channel === 'custom') return 'cover-custom'
  return 'cover-general'
}

export const formatWords = (words?: number) => {
  if (!words) return '0字'
  if (words >= 10000) {
    return (words / 10000).toFixed(1) + '万字'
  }
  return words + '字'
}