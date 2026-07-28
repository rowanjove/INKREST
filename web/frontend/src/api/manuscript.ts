import type { JSONContent } from '@tiptap/core'
import type {
  ManuscriptDocument,
  ManuscriptRevision,
  ManuscriptWorkspace,
} from '../entities/manuscript/manuscript'
import api from './client'

export const getManuscriptWorkspace = (params?: {
  chapter_id?: string
  query?: string
  status?: string
}) => api.get<ManuscriptWorkspace>('/manuscript/workspace', { params })

export const saveManuscriptDocument = (
  chapterId: string,
  data: {
    title: string
    content_json: JSONContent
    expected_revision: number
    source: 'autosave' | 'manual' | 'ai_accept'
  },
) => api.put<ManuscriptDocument>(`/manuscript/documents/${chapterId}`, data)

export const listManuscriptRevisions = (chapterId: string) =>
  api.get<ManuscriptRevision[]>(`/manuscript/documents/${chapterId}/revisions`)

export const restoreManuscriptRevision = (
  chapterId: string,
  revisionId: string,
  expectedRevision: number,
) =>
  api.post<ManuscriptDocument>(
    `/manuscript/documents/${chapterId}/revisions/${revisionId}/restore`,
    { expected_revision: expectedRevision },
  )
