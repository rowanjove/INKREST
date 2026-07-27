import { BrowserWindow, shell } from 'electron'

import { isAllowedAppUrl, isAllowedExternalUrl } from './security'

export function applyWindowSecurity(
  window: BrowserWindow,
  origins: ReadonlySet<string>,
  externalHosts: ReadonlySet<string> = new Set(),
): void {
  const { webContents } = window

  webContents.on('will-navigate', (event, targetUrl) => {
    if (!isAllowedAppUrl(targetUrl, origins)) {
      event.preventDefault()
    }
  })

  webContents.on('will-redirect', (event, targetUrl) => {
    if (!isAllowedAppUrl(targetUrl, origins)) {
      event.preventDefault()
    }
  })

  webContents.on('will-attach-webview', (event) => {
    event.preventDefault()
  })

  webContents.setWindowOpenHandler(({ url }) => {
    if (isAllowedExternalUrl(url, externalHosts)) {
      void shell.openExternal(url).catch((error) => {
        console.error(`Failed to open external URL: ${String(error)}`)
      })
    }
    return { action: 'deny' }
  })

  webContents.session.setPermissionRequestHandler(
    (_webContents, _permission, callback) => callback(false),
  )
}
