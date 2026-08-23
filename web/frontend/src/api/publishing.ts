import type {
  ExportFormat,
  PublishingExportTask,
  PublishingWorkspace,
} from '../entities/publishing/publishing'
import api from './client'

export const getPublishingWorkspace = (
  chapterId = '',
  params: { query?: string; offset?: number; limit?: number } = {},
) =>
  api.get<PublishingWorkspace>('/publishing/workspace', {
    params: {
      ...(chapterId ? { chapter_id: chapterId } : {}),
      ...params,
    },
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
}) => api.post<PublishingExportTask>('/publishing/export', data)

export const getPublishingExportTask = (taskId: string) =>
  api.get<PublishingExportTask>(`/publishing/export/${taskId}`)

export const downloadPublishingExport = (taskId: string) =>
  api.get<Blob>(`/publishing/export/${taskId}/download`, { responseType: 'blob' })

export const cancelPublishingExport = (taskId: string) =>
  api.post<{ task_id: string; status: string }>(`/publishing/export/${taskId}/cancel`)
