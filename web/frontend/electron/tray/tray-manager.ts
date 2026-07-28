import { Tray, Menu, BrowserWindow, nativeImage, app } from 'electron';
import path from 'path';

export function createTray(mainWindow: BrowserWindow): Tray {
  const iconPath = app.isPackaged
    ? path.join(process.resourcesPath, 'app.asar.unpacked', 'build', 'tray_icon.png')
    : path.join(__dirname, '..', '..', 'build', 'tray_icon.png');
  let icon: Electron.NativeImage;

  try {
    icon = nativeImage.createFromPath(iconPath);
    if (icon.isEmpty()) throw new Error('empty');
  } catch {
    // Fallback: create a simple colored icon
    icon = nativeImage.createEmpty();
  }

  const tray = new Tray(icon);
  tray.setToolTip('栖墨 · INKREST - 智能长篇写作空间');

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示主窗口',
      click: () => {
        mainWindow.show();
        mainWindow.focus();
      },
    },
    { type: 'separator' },
    {
      label: '运行新章节',
      click: () => {
        mainWindow.show();
        mainWindow.focus();
        mainWindow.webContents.send('navigate', '/');
      },
    },
    {
      label: '查看状态库',
      click: () => {
        mainWindow.show();
        mainWindow.focus();
        mainWindow.webContents.send('navigate', '/state');
      },
    },
    { type: 'separator' },
    {
      label: '退出栖墨',
      click: () => {
        (app as any).isQuitting = true;
        app.quit();
      },
    },
  ]);

  tray.setContextMenu(contextMenu);

  tray.on('double-click', () => {
    mainWindow.show();
    mainWindow.focus();
  });

  return tray;
}
