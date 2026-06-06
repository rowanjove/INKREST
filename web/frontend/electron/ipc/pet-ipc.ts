import { BrowserWindow, Menu, app, ipcMain, screen } from 'electron';
import { PetSettings, readPetSettings, writePetSettings } from '../pet-settings';
import { createBubbleWindow, positionBubbleNearPet } from '../windows/bubble-window';
import { createPetWindow } from '../windows/pet-window';

export interface PetIpcContext {
  isDev: boolean;
  apiPort: number;
  getMainWindow: () => BrowserWindow | null;
  getPetWindow: () => BrowserWindow | null;
  setPetWindow: (window: BrowserWindow | null) => void;
  getBubbleWindow: () => BrowserWindow | null;
  setBubbleWindow: (window: BrowserWindow | null) => void;
  navigateMain: (route: string) => void;
}

export function ensurePetWindow(ctx: PetIpcContext) {
  let petWindow = ctx.getPetWindow();
  if (petWindow && !petWindow.isDestroyed()) {
    return petWindow;
  }
  const settings = readPetSettings();
  petWindow = createPetWindow({ settings, isDev: ctx.isDev, apiPort: ctx.apiPort });
  petWindow.on('closed', () => {
    ctx.setPetWindow(null);
  });
  ctx.setPetWindow(petWindow);
  return petWindow;
}

function ensureBubbleWindow(ctx: PetIpcContext) {
  const petWindow = ensurePetWindow(ctx);
  let bubbleWindow = ctx.getBubbleWindow();
  if (bubbleWindow && !bubbleWindow.isDestroyed()) {
    positionBubbleNearPet(bubbleWindow, petWindow);
    return bubbleWindow;
  }
  bubbleWindow = createBubbleWindow({ petWindow, isDev: ctx.isDev, apiPort: ctx.apiPort });
  bubbleWindow.on('closed', () => {
    ctx.setBubbleWindow(null);
  });
  bubbleWindow.on('blur', () => {
    bubbleWindow?.hide();
  });
  ctx.setBubbleWindow(bubbleWindow);
  return bubbleWindow;
}

function applySettingsToPetWindow(settings: PetSettings, petWindow: BrowserWindow | null) {
  if (!petWindow || petWindow.isDestroyed()) return;
  petWindow.setAlwaysOnTop(settings.alwaysOnTop);
  petWindow.setSize(settings.size, settings.size);
  if (settings.position) {
    petWindow.setPosition(settings.position.x, settings.position.y);
  }
  if (!settings.enabled) {
    petWindow.hide();
  }
}

export function registerPetIpc(ctx: PetIpcContext) {
  ipcMain.handle('pet:getWindowBounds', () => {
    const petWindow = ctx.getPetWindow();
    if (petWindow && !petWindow.isDestroyed()) {
      return petWindow.getBounds();
    }
    return null;
  });

  ipcMain.handle('pet:getWorkArea', () => {
    const petWindow = ctx.getPetWindow();
    if (petWindow && !petWindow.isDestroyed()) {
      const display = screen.getDisplayMatching(petWindow.getBounds());
      return display.workArea;
    }
    return screen.getPrimaryDisplay().workArea;
  });

  ipcMain.handle('pet:setWindowBounds', (_event, bounds: { x: number; y: number; width?: number; height?: number }) => {
    const petWindow = ctx.getPetWindow();
    if (petWindow && !petWindow.isDestroyed()) {
      const currentBounds = petWindow.getBounds();
      petWindow.setBounds({
        x: Math.round(bounds.x),
        y: Math.round(bounds.y),
        width: bounds.width !== undefined ? Math.round(bounds.width) : currentBounds.width,
        height: bounds.height !== undefined ? Math.round(bounds.height) : currentBounds.height,
      });
    }
  });

  ipcMain.handle('pet:getSettings', () => readPetSettings());

  ipcMain.handle('pet:updateSettings', (_event, patch: Partial<PetSettings>) => {
    const settings = writePetSettings(patch);
    applySettingsToPetWindow(settings, ctx.getPetWindow());
    if (settings.enabled && settings.showOnStartup) {
      ensurePetWindow(ctx).showInactive();
    }
    return settings;
  });

  ipcMain.handle('pet:show', () => {
    writePetSettings({ enabled: true });
    ensurePetWindow(ctx).showInactive();
  });

  ipcMain.handle('pet:hide', () => {
    writePetSettings({ enabled: false });
    ctx.getBubbleWindow()?.hide();
    ctx.getPetWindow()?.hide();
  });

  ipcMain.handle('pet:toggleBubble', () => {
    const bubbleWindow = ensureBubbleWindow(ctx);
    if (bubbleWindow.isVisible()) {
      bubbleWindow.hide();
    } else {
      positionBubbleNearPet(bubbleWindow, ensurePetWindow(ctx));
      bubbleWindow.showInactive();
    }
  });

  ipcMain.handle('pet:moveBy', (_event, delta: { x: number; y: number }) => {
    const petWindow = ensurePetWindow(ctx);
    const bounds = petWindow.getBounds();
    petWindow.setPosition(bounds.x + Math.round(delta.x), bounds.y + Math.round(delta.y));
  });

  ipcMain.handle('pet:savePosition', () => {
    const petWindow = ctx.getPetWindow();
    if (petWindow && !petWindow.isDestroyed()) {
      const { x, y } = petWindow.getBounds();
      writePetSettings({ position: { x, y } });
    }
  });

  ipcMain.handle('pet:openMain', () => {
    const mainWindow = ctx.getMainWindow();
    mainWindow?.show();
    mainWindow?.focus();
  });

  ipcMain.handle('pet:navigateMain', (_event, route: string) => {
    ctx.navigateMain(route);
  });

  ipcMain.handle('pet:showContextMenu', () => {
    const petWindow = ensurePetWindow(ctx);
    const menu = Menu.buildFromTemplate([
      { label: '打开主界面', click: () => ctx.navigateMain('/') },
      { label: '任务监控', click: () => ctx.navigateMain('/monitor?tab=tasks') },
      { label: '日志', click: () => ctx.navigateMain('/logs') },
      { type: 'separator' },
      {
        label: '隐藏山山',
        click: () => {
          writePetSettings({ enabled: false });
          ctx.getBubbleWindow()?.hide();
          ctx.getPetWindow()?.hide();
        },
      },
      { label: '退出栖墨', click: () => { (app as any).isQuitting = true; app.quit(); } },
    ]);
    menu.popup({ window: petWindow });
  });
}
