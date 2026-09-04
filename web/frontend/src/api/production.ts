import type { ProductionReviewQueue, ProductionWorkspace } from '../entities/production/production'
import api from './client'

export const getProductionWorkspace = () =>
  api.get<ProductionWorkspace>('/production/workspace')

export interface ProductionReviewParams {
  cursor?: string
  limit?: number
  severity?: string
  stage?: string
}

export const getProductionReviews = (params?: ProductionReviewParams) =>
  api.get<ProductionReviewQueue>('/production/reviews', { params })

