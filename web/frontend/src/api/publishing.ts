import type {
  ExportFormat,
  PublishingWorkspace,
} from '../entities/publishing/publishing'
import api from './client'

export const getPublishingWorkspace = (chapterId = '') =>
  api.get<PublishingWorkspace>('/publishing/workspace', {
    params: chapterId ? { chapter_id: chapterId } : undefined,
  })

export const updatePublishingPlatform = (platform: string) =>
  api.put<PublishingWorkspace>('/publishing/platform', { platform })

export const savePublishingFeedback = (data: {
  chapter_id: string
  bounce_rate: number
  retention_rate: number
  active_readers: number
}) => api.put<PublishingWorkspace>('/publishing/feedback', data)

export const exportPublication = (data: {
  format: ExportFormat
  title: string
  chapter_ids: string[]
  acknowledge_warnings: boolean
}) => api.post<Blob>('/publishing/export', data, { responseType: 'blob' })
