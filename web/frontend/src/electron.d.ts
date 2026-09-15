interface ElectronPetSettings {
  enabled: boolean;
  showOnStartup: boolean;
  alwaysOnTop: boolean;
  size: number;
  position: { x: number; y: number } | null;
  notifyOnTaskComplete: boolean;
  notifyOnTaskError: boolean;
  petId: string;
  dockedEdge?: 'left' | 'right' | 'top' | null;
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

// Legacy ids remain readable for migration, but the main process accepts and
// applies only the official GitHub channel.
type ElectronUpdateSourceId = 'github' | 'ghproxy' | 'mirror' | 'custom';

interface ElectronUpdateSettings {
  autoCheck: boolean;
  autoDownload: boolean;
  sourceId: ElectronUpdateSourceId;
  customSourceUrl: string;
  checkPrerelease: boolean;
  lastCheckedAt: number | null;
}

type ElectronUpdaterState =
  | 'idle'
  | 'checking'
  | 'available'
  | 'not-available'
  | 'downloading'
  | 'downloaded'
  | 'error';

interface ElectronUpdateInfo {
  version: string;
  releaseDate?: string;
  releaseNotes?: string;
  files?: Array<{ url?: string; size?: number }>;
}

interface ElectronUpdateProgress {
  percent: number;
  bytesPerSecond: number;
  transferred: number;
  total: number;
}

interface ElectronUpdaterStatusSnapshot {
  state: ElectronUpdaterState;
  currentVersion: string;
  updateInfo?: ElectronUpdateInfo;
  progress?: ElectronUpdateProgress;
  error?: string;
  sourceId: ElectronUpdateSourceId;
  effectiveFeedUrl: string;
  isPortable: boolean;
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
  animatePetWindowBounds: (
    bounds: { x: number; y: number; width?: number; height?: number },
    durationMs?: number,
  ) => Promise<void>;
  onNavigate: (callback: (route: string) => void) => () => void;
  onProgress: (callback: (data: unknown) => void) => () => void;
  onLog: (callback: (data: unknown) => void) => () => void;
  onComplete: (callback: (data: unknown) => void) => () => void;
  onError: (callback: (data: unknown) => void) => () => void;
  getBackendStatus: () => Promise<ElectronBackendStatus>;
  onBackendStatus: (callback: (status: ElectronBackendStatus) => void) => () => void;

  // Software updater
  getUpdateSettings: () => Promise<ElectronUpdateSettings>;
  updateUpdateSettings: (patch: Partial<ElectronUpdateSettings>) => Promise<ElectronUpdateSettings>;
  getUpdateStatus: () => Promise<ElectronUpdaterStatusSnapshot>;
  checkForUpdates: () => Promise<void>;
  downloadUpdate: () => Promise<void>;
  quitAndInstall: () => Promise<void>;
  openReleasePage: (url?: string) => Promise<void>;
  onUpdateStatus: (callback: (status: ElectronUpdaterStatusSnapshot) => void) => () => void;
}

interface Window {
  electronAPI?: ElectronAPI;
}
