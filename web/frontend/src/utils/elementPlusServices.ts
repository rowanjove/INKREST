type MessageBoxActionCarrier = {
  action?: unknown
}

export function isMessageBoxDismissal(reason: unknown): boolean {
  const action =
    typeof reason === 'string'
      ? reason
      : typeof reason === 'object' && reason !== null
        ? (reason as MessageBoxActionCarrier).action
        : undefined

  return action === 'cancel' || action === 'close'
}
