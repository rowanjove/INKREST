import { BrowserWindow, screen } from 'electron';
import path from 'path';

export function createBubbleWindow(options: {
  petWindow: BrowserWindow;
  isDev: boolean;
  apiPort: number;
}) {
  const { petWindow, isDev, apiPort } = options;
  const petBounds = petWindow.getBounds();
  const workArea = screen.getDisplayMatching(petBounds).workArea;
  const width = 340;
  const height = 520;
  const x = Math.max(workArea.x, petBounds.x + petBounds.width - width);
  const y = Math.max(workArea.y, petBounds.y - height + 24);

  const bubbleWindow = new BrowserWindow({
    width,
    height,
    x,
    y,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    hasShadow: false,
    show: false,
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  bubbleWindow.setMenu(null);
  bubbleWindow.setMenuBarVisibility(false);

  if (isDev) {
    bubbleWindow.loadURL('http://localhost:5173/pet-bubble');
  } else {
    bubbleWindow.loadURL(`http://127.0.0.1:${apiPort}/pet-bubble`);
  }

  return bubbleWindow;
}

export function positionBubbleNearPet(bubbleWindow: BrowserWindow, petWindow: BrowserWindow) {
  const petBounds = petWindow.getBounds();
  const bubbleBounds = bubbleWindow.getBounds();
  const workArea = screen.getDisplayMatching(petBounds).workArea;
  const x = Math.min(
    workArea.x + workArea.width - bubbleBounds.width,
    Math.max(workArea.x, petBounds.x + petBounds.width - bubbleBounds.width),
  );
  const y = Math.min(
    workArea.y + workArea.height - bubbleBounds.height,
    Math.max(workArea.y, petBounds.y - bubbleBounds.height + 24),
  );
  bubbleWindow.setBounds({ ...bubbleBounds, x, y });
}
