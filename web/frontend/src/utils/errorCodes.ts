/** User-facing labels for API / task failure codes (mirrors novel_agent.errors.codes). */

export const ERROR_CODE_HINTS: Record<string, string> = {
  LLM_NOT_READY: '请在「设置 → Agent 路由」选择可用的日常模型（非 Static 占位）并填写 API Key。',
  ARC_QUEUE_STALE: '卷队列与大纲不一致，请在工作台先点「同步卷队列」或重新 ensure-queue。',
  READINESS_BLOCKED: '开书清单未就绪，请按工作台提示补齐大纲、书名与核心资产。',
  CIRCUIT_PAUSED: '全书因质量熔断已暂停，建议先到章节维护改稿并重跑门禁，再续跑批量。',
  CHAPTER_ALREADY_RUNNING: '该章节已有任务在跑，请等待完成或在工作台生产线中止后再试。',
  NOVEL_BATCH_RUNNING: '全书批量任务已在运行，请等待结束后再启动新的续跑。',
  EXTERNAL_REVIEW_PENDING: '有待外审章节未通过，请先在章节详情标记外审通过或关闭该门禁。',
  LLM_AUTH: '模型 API 认证失败，请检查 Key 是否有效、是否过期。',
  LLM_RATE_LIMIT: '模型 API 触发限流，请稍后重试或切换备用模型。',
  LLM_TIMEOUT: '模型请求超时，可重试单章或降低并发。',
  LLM_RESPONSE: '模型返回格式异常，可重跑审校或单章。',
  TASK_ABORTED: '任务已被用户中止。',
  RECOVERABLE_PIPELINE: '本章可重试：查看运行日志后补跑单章或只重跑门禁。',
  VALIDATION: '请求参数或项目状态无效，请按提示修正后重试。',
  UNKNOWN: '发生未分类错误，请查看 logs/novel_agent.log 或日志中心。',
}

export function errorCodeHint(code: string | undefined | null, fallback?: string): string {
  if (!code) return fallback || ''
  return ERROR_CODE_HINTS[code] || fallback || `[${code}]`
}