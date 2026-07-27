import type { BrowserWindow } from 'electron';

/** Show only after first paint; avoids black/white flash on transparent or themed windows. */
export function showWhenReady(window: BrowserWindow, mode: 'show' | 'showInactive' = 'showInactive') {
  const reveal = () => {
    if (window.isDestroyed()) return;
    if (mode === 'show') {
      window.show();
    } else {
      window.showInactive();
    }
  };

  if (window.webContents.isLoadingMainFrame()) {
    window.once('ready-to-show', reveal);
    return;
  }
  reveal();
}