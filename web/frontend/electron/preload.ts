import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron';
import type { PetSettings } from './pet-settings';

type BackendState = 'online' | 'offline' | 'restarting';

interface BackendStatusSnapshot {
  state: BackendState;
}

function parseBackendStatusSnapshot(value: unknown): BackendStatusSnapshot {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new TypeError('backend status must be an object');
  }
  const input = value as Record<string, unknown>;
  if (Object.keys(input).some((key) => key !== 'state')) {
    throw new TypeError('backend status contains unsupported fields');
  }
  if (!['online', 'offline', 'restarting'].includes(String(input.state))) {
    throw new TypeError('backend status state is invalid');
  }
  return { state: input.state as BackendState };
}

export interface ElectronAPI {
  // Pet assistant
  getPetSettings: () => Promise<PetSettings>;
  updatePetSettings: (patch: Partial<PetSettings>) => Promise<PetSettings>;
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
  onProgress: (callback: (data: unknown) => void) => () => void;
  onLog: (callback: (data: unknown) => void) => () => void;
  onComplete: (callback: (data: unknown) => void) => () => void;
  onError: (callback: (data: unknown) => void) => () => void;
  getBackendStatus: () => Promise<BackendStatusSnapshot>;
  onBackendStatus: (callback: (status: BackendStatusSnapshot) => void) => () => void;
}

const electronAPI: ElectronAPI = {
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
    const handler = (_event: IpcRendererEvent, route: string) => callback(route);
    ipcRenderer.on('app:navigate', handler);
    return () => ipcRenderer.removeListener('app:navigate', handler);
  },

  onProgress: (callback) => {
    const handler = (_event: IpcRendererEvent, data: unknown) => callback(data);
    ipcRenderer.on('agent:progress', handler);
    return () => ipcRenderer.removeListener('agent:progress', handler);
  },

  onLog: (callback) => {
    const handler = (_event: IpcRendererEvent, data: unknown) => callback(data);
    ipcRenderer.on('agent:log', handler);
    return () => ipcRenderer.removeListener('agent:log', handler);
  },

  onComplete: (callback) => {
    const handler = (_event: IpcRendererEvent, data: unknown) => callback(data);
    ipcRenderer.on('agent:complete', handler);
    return () => ipcRenderer.removeListener('agent:complete', handler);
  },

  onError: (callback) => {
    const handler = (_event: IpcRendererEvent, data: unknown) => callback(data);
    ipcRenderer.on('agent:error', handler);
    return () => ipcRenderer.removeListener('agent:error', handler);
  },

  getBackendStatus: async () =>
    parseBackendStatusSnapshot(await ipcRenderer.invoke('app:getBackendStatus')),
  onBackendStatus: (callback) => {
    const handler = (_event: IpcRendererEvent, status: unknown) =>
      callback(parseBackendStatusSnapshot(status));
    ipcRenderer.on('backend:status', handler);
    return () => ipcRenderer.removeListener('backend:status', handler);
  },
};

contextBridge.exposeInMainWorld('electronAPI', electronAPI);
