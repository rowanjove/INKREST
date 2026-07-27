import { app, BrowserWindow, ipcMain, Menu, Tray } from 'electron';
import net from 'net';
import path from 'path';
import { PythonBridge } from './agents/python-bridge';
import { ensurePetWindow, registerPetIpc } from './ipc/pet-ipc';
import { readPetSettings } from './pet-settings';
import { createTray } from './tray/tray-manager';
import { initAutoUpdater } from './updater/auto-updater';

let mainWindow: BrowserWindow | null = null;
let petWindow: BrowserWindow | null = null;
let bubbleWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let pythonBridge: PythonBridge;

const isDev = !app.isPackaged;
let apiPort = 8000;

const gotSingleInstanceLock = app.requestSingleInstanceLock();

if (!gotSingleInstanceLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (!mainWindow) return;
    if (mainWindow.isMinimized()) mainWindow.restore();
    if (!mainWindow.isVisible()) mainWindow.show();
    mainWindow.focus();
  });
}

function resolveAppIcon() {
  const iconName = process.platform === 'win32' ? 'icon.ico' : 'icon.png';
  return isDev
    ? path.join(__dirname, '..', 'build', iconName)
    : path.join(process.resourcesPath, 'app.asar.unpacked', 'build', iconName);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    title: '栖墨 · INKREST',
    icon: resolveAppIcon(),
    autoHideMenuBar: true,
    show: false,
    backgroundColor: '#f6f4f1',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });
  mainWindow.once('ready-to-show', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.maximize();
      mainWindow.show();
    }
  });
  mainWindow.setMenu(null);
  mainWindow.setMenuBarVisibility(false);

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadURL(`http://127.0.0.1:${apiPort}`);
  }

  mainWindow.on('close', (event) => {
    if (!(app as any).isQuitting) {
      event.preventDefault();
      mainWindow?.hide();
    }
  });

  return mainWindow;
}

function appUrl(route = '/') {
  const normalized = route.startsWith('/') ? route : `/${route}`;
  if (isDev) {
    return `http://localhost:5173${normalized}`;
  }
  return `http://127.0.0.1:${apiPort}${normalized}`;
}

function navigateMain(route: string) {
  if (!mainWindow || mainWindow.isDestroyed()) {
    createWindow();
    mainWindow?.loadURL(appUrl(route));
  } else {
    mainWindow?.show();
    mainWindow?.focus();
    mainWindow?.webContents.send('app:navigate', route);
  }
}

// ---- IPC Handlers ----

function registerIpcHandlers() {
  ipcMain.handle('app:getPort', () => apiPort);
  ipcMain.handle('app:getBackendStatus', () => isRestarting ? 'restarting' : 'online');

  ipcMain.handle('chapter:run', async (_event, params: { chapter_id: string; goal: string; dry_run?: boolean }) => {
    try {
      const result = await pythonBridge.runChapter(params.chapter_id, params.goal, params.dry_run);
      return { success: true, data: result };
    } catch (error: any) {
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('chapter:abort', () => {
    pythonBridge.abort();
    return { success: true };
  });

  ipcMain.handle('app:getUserDataPath', () => {
    return app.getPath('userData');
  });

  ipcMain.handle('window:minimizeToTray', () => {
    mainWindow?.hide();
  });

  registerPetIpc({
    isDev,
    apiPort,
    getMainWindow: () => mainWindow,
    getPetWindow: () => petWindow,
    setPetWindow: (window) => {
      petWindow = window;
    },
    getBubbleWindow: () => bubbleWindow,
    setBubbleWindow: (window) => {
      bubbleWindow = window;
    },
    navigateMain,
  });
}

let watchdogTimer: NodeJS.Timeout | null = null;
let consecutiveFailures = 0;
let isRestarting = false;

function startWatchdog() {
  if (watchdogTimer) clearInterval(watchdogTimer);
  
  watchdogTimer = setInterval(async () => {
    if ((app as any).isQuitting || isRestarting) return;
    
    try {
      const res = await fetch(`http://127.0.0.1:${apiPort}/api/health`);
      if (res.ok) {
        consecutiveFailures = 0;
        return;
      }
    } catch (err) {
      // Fetch failed
    }
    
    consecutiveFailures++;
    console.warn(`[Watchdog] Backend health check failed (${consecutiveFailures}/3)`);
    
    if (consecutiveFailures >= 3) {
      console.error(`[Watchdog] Backend unresponsive. Triggering automatic restart...`);
      isRestarting = true;
      consecutiveFailures = 0;
      
      mainWindow?.webContents.send('backend:status', 'restarting');
      
      try {
        pythonBridge.stopServer();
        await new Promise(resolve => setTimeout(resolve, 1500));
        await pythonBridge.startServer(apiPort);
        isRestarting = false;
        mainWindow?.webContents.send('backend:status', 'online');
        console.log(`[Watchdog] Backend successfully restarted.`);
      } catch (restartErr: any) {
        isRestarting = false;
        mainWindow?.webContents.send('backend:status', 'offline');
        console.error(`[Watchdog] Failed to restart backend: ${restartErr.message}`);
      }
    }
  }, 5000);
}

// ---- App Lifecycle ----

function findAvailablePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      if (!address || typeof address === 'string') {
        server.close();
        reject(new Error('Unable to allocate an API port'));
        return;
      }
      server.close(() => resolve(address.port));
    });
  });
}

app.whenReady().then(async () => {
  app.setName('栖墨');
  Menu.setApplicationMenu(null);
  pythonBridge = new PythonBridge(isDev ? undefined : app.getPath('userData'));
  apiPort = isDev ? 8000 : await findAvailablePort();

  // 1. Start Python/FastAPI server. In dev this also makes the Vite proxy usable.
  try {
    await pythonBridge.startServer(apiPort);
    startWatchdog();
  } catch (err: any) {
    const { dialog } = require('electron');
    dialog.showErrorBox(
      '后端服务启动失败',
      `无法启动本地 Python 服务，错误信息:\n${err.message || err}\n\n请本进程正在使用的端口 ${apiPort} 未被占用且系统未限制该端口。`
    );
    app.quit();
    return;
  }

  // 2. Create main window.
  createWindow();

  // 3. System tray
  if (mainWindow) {
    tray = createTray(mainWindow);
  }

  // 4. IPC handlers
  registerIpcHandlers();

  // 5. Pet assistant window
  const petSettings = readPetSettings();
  if (petSettings.enabled && petSettings.showOnStartup) {
    ensurePetWindow({
      isDev,
      apiPort,
      getMainWindow: () => mainWindow,
      getPetWindow: () => petWindow,
      setPetWindow: (window) => {
        petWindow = window;
      },
      getBubbleWindow: () => bubbleWindow,
      setBubbleWindow: (window) => {
        bubbleWindow = window;
      },
      navigateMain,
    });
  }

  // 6. Auto updater (production only)
  if (!isDev) {
    initAutoUpdater(mainWindow!);
  }

  // 7. Forward Python bridge events to renderer
  pythonBridge.on('progress', (data) => {
    mainWindow?.webContents.send('agent:progress', data);
  });

  pythonBridge.on('log', (data) => {
    mainWindow?.webContents.send('agent:log', data);
  });

  pythonBridge.on('complete', (data) => {
    mainWindow?.webContents.send('agent:complete', data);
  });

  pythonBridge.on('error', (data) => {
    mainWindow?.webContents.send('agent:error', data);
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow) {
    mainWindow.show();
  }
});

app.on('before-quit', () => {
  (app as any).isQuitting = true;
  if (watchdogTimer) {
    clearInterval(watchdogTimer);
    watchdogTimer = null;
  }
  bubbleWindow?.destroy();
  petWindow?.destroy();
  pythonBridge?.abort();
  pythonBridge?.stopServer();
});
