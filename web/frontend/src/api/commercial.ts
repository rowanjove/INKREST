import api from './client'

export interface CommercialStatus {
  license: {
    tier: string
    is_valid: boolean
    validation_message: string
    has_active_license: boolean
    details?: {
      licensee: string
      tier: string
      issued_at: string
      expires_at?: string | null
      signature_valid: boolean
    } | null
    entitlements: string[]
  }
  vault: {
    vault_id: string
    storage_path: string
    is_safe: boolean
  }
  recovery: {
    sqlite_health: string
    integrity_ok: boolean
    crash_recovery: {
      active_session_count: number
    }
  }
  budget: {
    daily_budget_cny: number
    task_budget_cny: number
    today_spent_cny: number
    today_tokens_used: number
  }
}

export interface HealthCheckResult {
  status: 'healthy' | 'warning' | 'error'
  issues: string[]
  repaired?: string[]
}

export interface BackupResult {
  status: string
  backup_file: string
  size_bytes: number
  sha256: string
}

export interface DiagnosticResult {
  status: string
  report_file: string
  items: Record<string, any>
}

export interface CostEstimateResult {
  num_chapters: number
  model: string
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  estimated_cost_cny: number
  daily_budget_remaining_cny: number
  fits_daily_budget: boolean
}

export async function fetchCommercialStatus(): Promise<CommercialStatus> {
  const { data } = await api.get<CommercialStatus>('/commercial/status')
  return data
}

export async function startTrialLicense(): Promise<{ status: string; license: any; message: string }> {
  const { data } = await api.post('/commercial/license/trial')
  return data
}

export async function activateLicenseKey(licenseJson: string): Promise<{ status: string; license: any; message: string }> {
  const { data } = await api.post('/commercial/license/activate', { license_json: licenseJson })
  return data
}

export async function checkSystemHealth(): Promise<HealthCheckResult> {
  const { data } = await api.post<HealthCheckResult>('/commercial/recovery/health-check')
  return data
}

export async function repairSystemHealth(): Promise<HealthCheckResult> {
  const { data } = await api.post<HealthCheckResult>('/commercial/recovery/auto-repair')
  return data
}

export async function createCommercialBackup(): Promise<BackupResult> {
  const { data } = await api.post<BackupResult>('/commercial/recovery/backup')
  return data
}

export async function generateDiagnostics(): Promise<DiagnosticResult> {
  const { data } = await api.post<DiagnosticResult>('/commercial/recovery/diagnostics')
  return data
}

export async function estimateTaskCost(params: {
  num_chapters: number
  avg_input_tokens?: number
  avg_output_tokens?: number
  model?: string
}): Promise<CostEstimateResult> {
  const { data } = await api.post<CostEstimateResult>('/commercial/budget/estimate', params)
  return data
}
