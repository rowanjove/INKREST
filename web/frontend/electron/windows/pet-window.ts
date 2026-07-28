import { BrowserWindow } from 'electron';
import path from 'path';
import { PetSettings, clampPetPosition } from '../pet-settings';
import { appOrigins } from '../security';
import { applyWindowSecurity } from '../window-security';
import { showWhenReady } from './window-ready';

export function createPetWindow(options: {
  settings: PetSettings;
  isDev: boolean;
  apiPort: number;
}) {
  const { settings, isDev, apiPort } = options;
  const position = clampPetPosition(settings.position, settings.size);
  const petWindow = new BrowserWindow({
    width: settings.size,
    height: settings.size,
    x: position.x,
    y: position.y,
    frame: false,
    transparent: true,
    alwaysOnTop: settings.alwaysOnTop,
    resizable: false,
    skipTaskbar: true,
    hasShadow: false,
    show: false,
    backgroundColor: '#00000000',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  applyWindowSecurity(petWindow, appOrigins(isDev, apiPort));

  petWindow.setMenu(null);
  petWindow.setMenuBarVisibility(false);

  if (isDev) {
    petWindow.loadURL('http://localhost:5173/pet');
  } else {
    petWindow.loadURL(`http://127.0.0.1:${apiPort}/pet`);
  }

  showWhenReady(petWindow, 'showInactive');
  return petWindow;
}
