import { BrowserWindow, dialog, app } from 'electron';

// electron-updater is optional; gracefully handle missing dependency
let autoUpdater: any = null;

try {
  autoUpdater = require('electron-updater').autoUpdater;
} catch {
  console.warn('electron-updater not installed. Auto-update disabled.');
}

export function initAutoUpdater(mainWindow: BrowserWindow) {
  if (!autoUpdater) return;

  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = true;

  autoUpdater.on('checking-for-update', () => {
    console.log('Checking for updates...');
  });

  autoUpdater.on('update-available', async (info: any) => {
    const result = await dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: '发现新版本',
      message: `栖墨 ${info.version} 已发布`,
      detail: '是否现在下载更新？',
      buttons: ['下载更新', '稍后提醒'],
      defaultId: 0,
    });

    if (result.response === 0) {
      autoUpdater.downloadUpdate();
    }
  });

  autoUpdater.on('update-not-available', () => {
    console.log('App is up to date.');
  });

  autoUpdater.on('download-progress', (progress: any) => {
    mainWindow.webContents.send('updater:progress', {
      percent: progress.percent,
      transferred: progress.transferred,
      total: progress.total,
    });
  });

  autoUpdater.on('update-downloaded', async () => {
    const result = await dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: '更新已下载',
      message: '新版本已准备就绪',
      detail: '应用将重启以完成更新。',
      buttons: ['立即重启', '稍后重启'],
      defaultId: 0,
    });

    if (result.response === 0) {
      autoUpdater.quitAndInstall();
    }
  });

  autoUpdater.on('error', (err: any) => {
    console.error('Auto-updater error:', err);
  });

  // Check for updates on startup (with a delay)
  setTimeout(() => {
    autoUpdater.checkForUpdates().catch((err: any) => {
      console.error('Update check failed:', err);
    });
  }, 10000);
}
