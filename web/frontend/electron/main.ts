import {
  app,
  BrowserWindow,
  ipcMain,
  Menu,
  session,
  Tray,
  type IpcMainInvokeEvent,
} from 'electron';
import net from 'net';
import path from 'path';
import { PythonBridge } from './agents/python-bridge';
import { ensurePetWindow, registerPetIpc } from './ipc/pet-ipc';
import { readPetSettings } from './pet-settings';
import { createTray } from './tray/tray-manager';
import { initAutoUpdater } from './updater/auto-updater';
import {
  appOrigins,
  assertTrustedSenderUrl,
  backendStatusSnapshot,
  type BackendState,
} from './security';
import { applyWindowSecurity, hardenSessionPermissions } from './window-security';

app.enableSandbox();

let mainWindow: BrowserWindow | null = null;
let petWindow: BrowserWindow | null = null;
let bubbleWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let pythonBridge: PythonBridge | null = null;

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
      sandbox: true,
    },
  });
  applyWindowSecurity(mainWindow, appOrigins(isDev, apiPort));
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

function assertTrustedIpc(event: IpcMainInvokeEvent): void {
  const frame = event.senderFrame;
  if (!frame || frame.top !== frame) {
    throw new Error('Untrusted IPC frame');
  }
  assertTrustedSenderUrl(frame.url, appOrigins(isDev, apiPort));
}

function registerIpcHandlers() {
  ipcMain.handle('app:getBackendStatus', (event) => {
    assertTrustedIpc(event);
    return backendStatusSnapshot(isRestarting ? 'restarting' : 'online');
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
    assertTrustedSender: assertTrustedIpc,
  });
}

let watchdogTimer: NodeJS.Timeout | null = null;
let consecutiveFailures = 0;
let isRestarting = false;

function sendBackendStatus(state: BackendState): void {
  mainWindow?.webContents.send('backend:status', backendStatusSnapshot(state));
}

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
      
      sendBackendStatus('restarting');
      
      try {
        await pythonBridge?.stopServer();
        await pythonBridge?.startServer(apiPort);
        isRestarting = false;
        sendBackendStatus('online');
        console.log(`[Watchdog] Backend successfully restarted.`);
      } catch (restartErr: any) {
        isRestarting = false;
        sendBackendStatus('offline');
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

if (gotSingleInstanceLock) {
app.whenReady().then(async () => {
  app.setName('栖墨');
  Menu.setApplicationMenu(null);
  hardenSessionPermissions(session.defaultSession);
  const bridge = new PythonBridge(isDev ? undefined : app.getPath('userData'));
  pythonBridge = bridge;
  apiPort = isDev ? 8000 : await findAvailablePort();

  // 1. Start Python/FastAPI server. In dev this also makes the Vite proxy usable.
  try {
    await bridge.startServer(apiPort);
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
      assertTrustedSender: assertTrustedIpc,
    });
  }

  // 6. Auto updater (production only)
  if (!isDev) {
    initAutoUpdater(mainWindow!);
  }

  // 7. Forward Python bridge events to renderer
  bridge.on('progress', (data) => {
    mainWindow?.webContents.send('agent:progress', data);
  });

  bridge.on('log', (data) => {
    mainWindow?.webContents.send('agent:log', data);
  });

  bridge.on('complete', (data) => {
    mainWindow?.webContents.send('agent:complete', data);
  });

  bridge.on('error', (data) => {
    mainWindow?.webContents.send('agent:error', data);
  });
});
}

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

let shutdownInProgress = false;
let shutdownComplete = false;

app.on('before-quit', (event) => {
  (app as any).isQuitting = true;
  if (shutdownComplete) return;
  event.preventDefault();
  if (shutdownInProgress) return;
  shutdownInProgress = true;
  if (watchdogTimer) {
    clearInterval(watchdogTimer);
    watchdogTimer = null;
  }
  bubbleWindow?.destroy();
  petWindow?.destroy();
  const bridge = pythonBridge;
  bridge?.abort();
  void (async () => {
    try {
      await bridge?.stopServer();
    } finally {
      shutdownComplete = true;
      app.quit();
    }
  })();
});
