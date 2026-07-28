interface ElectronPetSettings {
  enabled: boolean;
  showOnStartup: boolean;
  alwaysOnTop: boolean;
  size: number;
  position: { x: number; y: number } | null;
  notifyOnTaskComplete: boolean;
  notifyOnTaskError: boolean;
  petId: string;
}

interface ElectronRectangle {
  x: number;
  y: number;
  width: number;
  height: number;
}

interface ElectronBackendStatus {
  state: 'online' | 'offline' | 'restarting';
}

interface ElectronAPI {
  getPetSettings: () => Promise<ElectronPetSettings>;
  updatePetSettings: (
    patch: Partial<ElectronPetSettings>,
  ) => Promise<ElectronPetSettings>;
  showPet: () => Promise<void>;
  hidePet: () => Promise<void>;
  togglePetBubble: () => Promise<void>;
  movePetBy: (delta: { x: number; y: number }) => Promise<void>;
  savePetPosition: () => Promise<void>;
  openMainWindow: () => Promise<void>;
  navigateMain: (route: string) => Promise<void>;
  showPetContextMenu: () => Promise<void>;
  getPetWorkArea: () => Promise<ElectronRectangle>;
  getPetWindowBounds: () => Promise<ElectronRectangle | null>;
  setPetWindowBounds: (bounds: { x: number; y: number; width?: number; height?: number }) => Promise<void>;
  onNavigate: (callback: (route: string) => void) => () => void;
  onProgress: (callback: (data: unknown) => void) => () => void;
  onLog: (callback: (data: unknown) => void) => () => void;
  onComplete: (callback: (data: unknown) => void) => () => void;
  onError: (callback: (data: unknown) => void) => () => void;
  getBackendStatus: () => Promise<ElectronBackendStatus>;
  onBackendStatus: (callback: (status: ElectronBackendStatus) => void) => () => void;
}

interface Window {
  electronAPI?: ElectronAPI;
}
