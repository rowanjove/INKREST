import {
  BrowserWindow,
  Menu,
  app,
  ipcMain,
  screen,
  type IpcMainInvokeEvent,
} from 'electron';
import { PetSettings, readPetSettings, writePetSettings } from '../pet-settings';
import {
  parseAnimateBoundsPayload,
  parseMoveDelta,
  parsePetSettingsPatch,
  parseRoute,
  parseWindowBounds,
} from '../security';
import { createBubbleWindow, positionBubbleNearPet } from '../windows/bubble-window';
import { createPetWindow } from '../windows/pet-window';
import { showWhenReady } from '../windows/window-ready';

let activePetAnimationTimer: NodeJS.Timeout | null = null;
let activePetAnimationResolve: (() => void) | null = null;

function cancelPetAnimation() {
  if (activePetAnimationTimer) {
    clearInterval(activePetAnimationTimer);
    activePetAnimationTimer = null;
  }
  if (activePetAnimationResolve) {
    const resolve = activePetAnimationResolve;
    activePetAnimationResolve = null;
    resolve();
  }
}

export interface PetIpcContext {
  isDev: boolean;
  apiPort: number;
  getMainWindow: () => BrowserWindow | null;
  getPetWindow: () => BrowserWindow | null;
  setPetWindow: (window: BrowserWindow | null) => void;
  getBubbleWindow: () => BrowserWindow | null;
  setBubbleWindow: (window: BrowserWindow | null) => void;
  navigateMain: (route: string) => void;
  assertTrustedSender: (event: IpcMainInvokeEvent) => void;
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
  petWindow.setAlwaysOnTop(settings.alwaysOnTop, 'screen-saver');
  petWindow.setSize(settings.size, settings.size);
  if (settings.position) {
    petWindow.setPosition(settings.position.x, settings.position.y);
  }
  if (!settings.enabled) {
    petWindow.hide();
  } else {
    showWhenReady(petWindow, 'showInactive');
  }
}

export function registerPetIpc(ctx: PetIpcContext) {
  ipcMain.handle('pet:getWindowBounds', (event) => {
    ctx.assertTrustedSender(event);
    const petWindow = ctx.getPetWindow();
    if (petWindow && !petWindow.isDestroyed()) {
      return petWindow.getBounds();
    }
    return null;
  });

  ipcMain.handle('pet:getWorkArea', (event) => {
    ctx.assertTrustedSender(event);
    const petWindow = ctx.getPetWindow();
    if (petWindow && !petWindow.isDestroyed()) {
      const display = screen.getDisplayMatching(petWindow.getBounds());
      return display.workArea;
    }
    return screen.getPrimaryDisplay().workArea;
  });

  ipcMain.handle('pet:setWindowBounds', (event, rawBounds: unknown) => {
    ctx.assertTrustedSender(event);
    cancelPetAnimation();
    const bounds = parseWindowBounds(rawBounds);
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

  ipcMain.handle('pet:animateBounds', async (event, rawPayload: unknown) => {
    ctx.assertTrustedSender(event);
    cancelPetAnimation();
    const { bounds: target, durationMs = 220 } = parseAnimateBoundsPayload(rawPayload);
    const petWindow = ctx.getPetWindow();
    if (!petWindow || petWindow.isDestroyed()) return;

    const start = petWindow.getBounds();
    const targetX = Math.round(target.x);
    const targetY = Math.round(target.y);
    const targetW = target.width !== undefined ? Math.round(target.width) : start.width;
    const targetH = target.height !== undefined ? Math.round(target.height) : start.height;

    const dx = targetX - start.x;
    const dy = targetY - start.y;
    const dw = targetW - start.width;
    const dh = targetH - start.height;

    if (dx === 0 && dy === 0 && dw === 0 && dh === 0) return;

    const totalFrames = Math.max(6, Math.min(60, Math.round(durationMs / 16)));
    let frame = 0;

    return new Promise<void>((resolve) => {
      activePetAnimationResolve = resolve;
      activePetAnimationTimer = setInterval(() => {
        frame++;
        const t = frame / totalFrames;
        // Cubic ease-out: 1 - (1 - t)^3
        const ease = 1 - Math.pow(1 - t, 3);

        if (frame >= totalFrames) {
          if (!petWindow.isDestroyed()) {
            petWindow.setBounds({
              x: targetX,
              y: targetY,
              width: targetW,
              height: targetH,
            });
          }
          cancelPetAnimation();
        } else {
          if (!petWindow.isDestroyed()) {
            petWindow.setBounds({
              x: Math.round(start.x + dx * ease),
              y: Math.round(start.y + dy * ease),
              width: Math.round(start.width + dw * ease),
              height: Math.round(start.height + dh * ease),
            });
          }
        }
      }, 16);
    });
  });

  ipcMain.handle('pet:getSettings', (event) => {
    ctx.assertTrustedSender(event);
    return readPetSettings();
  });

  ipcMain.handle('pet:updateSettings', (event, rawPatch: unknown) => {
    ctx.assertTrustedSender(event);
    const patch = parsePetSettingsPatch(rawPatch);
    const settings = writePetSettings(patch);
    applySettingsToPetWindow(settings, ctx.getPetWindow());
    if (settings.enabled && settings.showOnStartup) {
      showWhenReady(ensurePetWindow(ctx), 'showInactive');
    }
    return settings;
  });

  ipcMain.handle('pet:show', (event) => {
    ctx.assertTrustedSender(event);
    const petWindow = ensurePetWindow(ctx);
    const primary = screen.getPrimaryDisplay().workArea;
    const settings = readPetSettings();
    const size = settings.size || 180;
    const safeX = primary.x + primary.width - size - 40;
    const safeY = primary.y + primary.height - size - 80;

    writePetSettings({
      enabled: true,
      dockedEdge: null,
      position: { x: safeX, y: safeY },
    });

    petWindow.setBounds({ x: safeX, y: safeY, width: size, height: size });
    petWindow.setAlwaysOnTop(true, 'screen-saver');
    showWhenReady(petWindow, 'show');
    petWindow.show();
    petWindow.focus();
  });

  ipcMain.handle('pet:hide', (event) => {
    ctx.assertTrustedSender(event);
    writePetSettings({ enabled: false });
    ctx.getBubbleWindow()?.hide();
    ctx.getPetWindow()?.hide();
  });

  ipcMain.handle('pet:toggleBubble', (event) => {
    ctx.assertTrustedSender(event);
    const bubbleWindow = ensureBubbleWindow(ctx);
    if (bubbleWindow.isVisible()) {
      bubbleWindow.hide();
    } else {
      positionBubbleNearPet(bubbleWindow, ensurePetWindow(ctx));
      showWhenReady(bubbleWindow, 'showInactive');
    }
  });

  ipcMain.handle('pet:moveBy', (event, rawDelta: unknown) => {
    ctx.assertTrustedSender(event);
    cancelPetAnimation();
    const delta = parseMoveDelta(rawDelta);
    const petWindow = ensurePetWindow(ctx);
    const bounds = petWindow.getBounds();
    petWindow.setPosition(bounds.x + Math.round(delta.x), bounds.y + Math.round(delta.y));
  });

  ipcMain.handle('pet:savePosition', (event) => {
    ctx.assertTrustedSender(event);
    const petWindow = ctx.getPetWindow();
    if (petWindow && !petWindow.isDestroyed()) {
      const { x, y } = petWindow.getBounds();
      writePetSettings({ position: { x, y } });
    }
  });

  ipcMain.handle('pet:openMain', (event) => {
    ctx.assertTrustedSender(event);
    const mainWindow = ctx.getMainWindow();
    mainWindow?.show();
    mainWindow?.focus();
  });

  ipcMain.handle('pet:navigateMain', (event, rawRoute: unknown) => {
    ctx.assertTrustedSender(event);
    ctx.navigateMain(parseRoute(rawRoute));
  });

  ipcMain.handle('pet:showContextMenu', (event) => {
    ctx.assertTrustedSender(event);
    const petWindow = ensurePetWindow(ctx);
    const menu = Menu.buildFromTemplate([
      { label: '打开主界面', click: () => ctx.navigateMain('/') },
      { label: '任务监控', click: () => ctx.navigateMain('/production?tab=runs') },
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
