import { ipcMain, type IpcMainInvokeEvent } from 'electron'
import { parseUpdateSettingsPatch } from '../security'
import {
  updaterManager,
  type UpdaterStatusSnapshot,
} from '../updater/auto-updater'
import { isAllowedReleasePageUrl, type UpdateSettings } from '../updater/update-settings'

export interface UpdaterIpcContext {
  assertTrustedSender: (event: IpcMainInvokeEvent) => void
}

export function registerUpdaterIpc(ctx: UpdaterIpcContext): void {
  ipcMain.handle('updater:getSettings', (event): UpdateSettings => {
    ctx.assertTrustedSender(event)
    return updaterManager.getSettings()
  })

  ipcMain.handle('updater:updateSettings', (event, patch: unknown): UpdateSettings => {
    ctx.assertTrustedSender(event)
    const validPatch = parseUpdateSettingsPatch(patch)
    return updaterManager.updateSettings(validPatch)
  })

  ipcMain.handle('updater:getStatus', (event): UpdaterStatusSnapshot => {
    ctx.assertTrustedSender(event)
    return updaterManager.getStatus()
  })

  ipcMain.handle('updater:checkForUpdates', async (event): Promise<void> => {
    ctx.assertTrustedSender(event)
    await updaterManager.checkForUpdates(true)
  })

  ipcMain.handle('updater:downloadUpdate', async (event): Promise<void> => {
    ctx.assertTrustedSender(event)
    await updaterManager.downloadUpdate()
  })

  ipcMain.handle('updater:quitAndInstall', (event): void => {
    ctx.assertTrustedSender(event)
    updaterManager.quitAndInstall()
  })

  ipcMain.handle('updater:openReleasePage', (event, url?: unknown): void => {
    ctx.assertTrustedSender(event)
    const safeUrl = isAllowedReleasePageUrl(url) ? url : undefined
    updaterManager.openReleasePage(safeUrl)
  })
}
