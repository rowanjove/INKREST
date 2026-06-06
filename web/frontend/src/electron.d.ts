interface ElectronAPI {
  getPort: () => Promise<number>;
  getUserDataPath: () => Promise<string>;
  runChapter: (params: { chapter_id: string; goal: string; dry_run?: boolean }) => Promise<{ success: boolean; data?: any; error?: string }>;
  abortChapter: () => Promise<{ success: boolean }>;
  minimizeToTray: () => Promise<void>;
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
  getPetWorkArea: () => Promise<any>;
  getPetWindowBounds: () => Promise<any>;
  setPetWindowBounds: (bounds: { x: number; y: number; width?: number; height?: number }) => Promise<void>;
  onNavigate: (callback: (route: string) => void) => () => void;
  onProgress: (callback: (data: any) => void) => () => void;
  onLog: (callback: (data: any) => void) => () => void;
  onComplete: (callback: (data: any) => void) => () => void;
  onError: (callback: (data: any) => void) => () => void;
  getBackendStatus: () => Promise<string>;
  onBackendStatus: (callback: (status: string) => void) => () => void;
}

interface Window {
  electronAPI?: ElectronAPI;
}
