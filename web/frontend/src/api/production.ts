import type { ProductionWorkspace } from '../entities/production/production'
import api from './client'

export const getProductionWorkspace = () =>
  api.get<ProductionWorkspace>('/production/workspace')
