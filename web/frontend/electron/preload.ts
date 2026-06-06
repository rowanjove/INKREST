import { contextBridge, ipcRenderer } from 'electron';

export interface ElectronAPI {
  // App
  getPort: () => Promise<number>;
  getUserDataPath: () => Promise<string>;

  // Chapter
  runChapter: (params: { chapter_id: string; goal: string; dry_run?: boolean }) => Promise<{ success: boolean; data?: any; error?: string }>;
  abortChapter: () => Promise<{ success: boolean }>;

  // Window
  minimizeToTray: () => Promise<void>;

  // Pet assistant
  getPetSettings: () => Promise<any>;
  updatePetSettings: (patch: Record<string, any>) => Promise<any>;
  showPet: () => Promise<void>;
  hidePet: () => Promise<void>;
  togglePetBubble: () => Promise<void>;
  movePetBy: (delta: { x: number; y: number }) => Promise<void>;
  savePetPosition: () => Promise<void>;
  openMainWindow: () => Promise<void>;
  navigateMain: (route: string) => Promise<void>;
  showPetContextMenu: () => Promise<void>;
  onNavigate: (callback: (route: string) => void) => () => void;
  getPetWindowBounds: () => Promise<{ x: number; y: number; width: number; height: number } | null>;
  getPetWorkArea: () => Promise<{ x: number; y: number; width: number; height: number } | null>;
  setPetWindowBounds: (bounds: { x: number; y: number; width?: number; height?: number }) => Promise<void>;

  // Agent events (one-way from main)
  onProgress: (callback: (data: any) => void) => () => void;
  onLog: (callback: (data: any) => void) => () => void;
  onComplete: (callback: (data: any) => void) => () => void;
  onError: (callback: (data: any) => void) => () => void;
  getBackendStatus: () => Promise<string>;
  onBackendStatus: (callback: (status: string) => void) => () => void;
}

const electronAPI: ElectronAPI = {
  getPort: () => ipcRenderer.invoke('app:getPort'),
  getUserDataPath: () => ipcRenderer.invoke('app:getUserDataPath'),

  runChapter: (params) => ipcRenderer.invoke('chapter:run', params),
  abortChapter: () => ipcRenderer.invoke('chapter:abort'),

  minimizeToTray: () => ipcRenderer.invoke('window:minimizeToTray'),

  getPetSettings: () => ipcRenderer.invoke('pet:getSettings'),
  updatePetSettings: (patch) => ipcRenderer.invoke('pet:updateSettings', patch),
  showPet: () => ipcRenderer.invoke('pet:show'),
  hidePet: () => ipcRenderer.invoke('pet:hide'),
  togglePetBubble: () => ipcRenderer.invoke('pet:toggleBubble'),
  movePetBy: (delta) => ipcRenderer.invoke('pet:moveBy', delta),
  savePetPosition: () => ipcRenderer.invoke('pet:savePosition'),
  openMainWindow: () => ipcRenderer.invoke('pet:openMain'),
  navigateMain: (route) => ipcRenderer.invoke('pet:navigateMain', route),
  showPetContextMenu: () => ipcRenderer.invoke('pet:showContextMenu'),
  getPetWindowBounds: () => ipcRenderer.invoke('pet:getWindowBounds'),
  getPetWorkArea: () => ipcRenderer.invoke('pet:getWorkArea'),
  setPetWindowBounds: (bounds) => ipcRenderer.invoke('pet:setWindowBounds', bounds),
  onNavigate: (callback) => {
    const handler = (_event: any, route: string) => callback(route);
    ipcRenderer.on('app:navigate', handler);
    return () => ipcRenderer.removeListener('app:navigate', handler);
  },

  onProgress: (callback) => {
    const handler = (_event: any, data: any) => callback(data);
    ipcRenderer.on('agent:progress', handler);
    return () => ipcRenderer.removeListener('agent:progress', handler);
  },

  onLog: (callback) => {
    const handler = (_event: any, data: any) => callback(data);
    ipcRenderer.on('agent:log', handler);
    return () => ipcRenderer.removeListener('agent:log', handler);
  },

  onComplete: (callback) => {
    const handler = (_event: any, data: any) => callback(data);
    ipcRenderer.on('agent:complete', handler);
    return () => ipcRenderer.removeListener('agent:complete', handler);
  },

  onError: (callback) => {
    const handler = (_event: any, data: any) => callback(data);
    ipcRenderer.on('agent:error', handler);
    return () => ipcRenderer.removeListener('agent:error', handler);
  },

  getBackendStatus: () => ipcRenderer.invoke('app:getBackendStatus'),
  onBackendStatus: (callback) => {
    const handler = (_event: any, status: string) => callback(status);
    ipcRenderer.on('backend:status', handler);
    return () => ipcRenderer.removeListener('backend:status', handler);
  },
};

contextBridge.exposeInMainWorld('electronAPI', electronAPI);
