import { app, Rectangle, screen } from 'electron';
import fs from 'fs';
import path from 'path';

export interface PetSettings {
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

const DEFAULT_SETTINGS: PetSettings = {
  enabled: true,
  showOnStartup: true,
  alwaysOnTop: true,
  size: 180,
  position: null,
  notifyOnTaskComplete: true,
  notifyOnTaskError: true,
  petId: 'shanshan',
  dockedEdge: null,
};

function settingsPath() {
  return path.join(app.getPath('userData'), 'pet-settings.json');
}

function clampNumber(value: unknown, min: number, max: number, fallback: number) {
  if (typeof value !== 'number' || Number.isNaN(value)) return fallback;
  return Math.min(max, Math.max(min, Math.round(value)));
}

export function clampPetPosition(
  position: { x: number; y: number } | null,
  size: number,
  dockedEdge?: 'left' | 'right' | 'top' | null,
) {
  const displays = screen.getAllDisplays();
  const raw = position;

  if (raw) {
    const matchedDisplay = displays.find((d) => {
      const wa = d.workArea;
      return (
        raw.x + size >= wa.x + 32 &&
        raw.x <= wa.x + wa.width - 32 &&
        raw.y + size >= wa.y + 32 &&
        raw.y <= wa.y + wa.height - 32
      );
    });

    if (matchedDisplay) {
      const wa = matchedDisplay.workArea;
      if (dockedEdge === 'left') {
        return {
          x: wa.x - size + 48,
          y: Math.min(wa.y + wa.height - size, Math.max(wa.y, Math.round(raw.y))),
        };
      }
      if (dockedEdge === 'right') {
        return {
          x: wa.x + wa.width - 48,
          y: Math.min(wa.y + wa.height - size, Math.max(wa.y, Math.round(raw.y))),
        };
      }
      if (dockedEdge === 'top') {
        return {
          x: Math.min(wa.x + wa.width - size, Math.max(wa.x, Math.round(raw.x))),
          y: wa.y - size + 48,
        };
      }
      return {
        x: Math.min(wa.x + wa.width - size, Math.max(wa.x, Math.round(raw.x))),
        y: Math.min(wa.y + wa.height - size, Math.max(wa.y, Math.round(raw.y))),
      };
    }
  }

  const primaryWA = screen.getPrimaryDisplay().workArea;
  const rawX = raw ? raw.x : primaryWA.x + primaryWA.width - size - 20;
  const rawY = raw ? raw.y : primaryWA.y + primaryWA.height - size - 20;

  return {
    x: Math.min(primaryWA.x + primaryWA.width - size, Math.max(primaryWA.x, Math.round(rawX))),
    y: Math.min(primaryWA.y + primaryWA.height - size, Math.max(primaryWA.y, Math.round(rawY))),
  };
}

export function normalizePetSettings(input: Partial<PetSettings> = {}): PetSettings {
  const size = clampNumber(input.size, 128, 260, DEFAULT_SETTINGS.size);
  const dockedEdge = (input.dockedEdge === 'left' || input.dockedEdge === 'right' || input.dockedEdge === 'top')
    ? input.dockedEdge
    : null;
  return {
    ...DEFAULT_SETTINGS,
    ...input,
    size,
    dockedEdge,
    position: input.position
      ? clampPetPosition(input.position, size, dockedEdge)
      : DEFAULT_SETTINGS.position,
    petId: input.petId || DEFAULT_SETTINGS.petId,
  };
}

export function readPetSettings(): PetSettings {
  const file = settingsPath();
  if (!fs.existsSync(file)) {
    return normalizePetSettings();
  }
  try {
    const parsed = JSON.parse(fs.readFileSync(file, 'utf-8'));
    return normalizePetSettings(parsed);
  } catch {
    try {
      fs.renameSync(file, `${file}.bak`);
    } catch {
      // Keep going with defaults if the damaged file cannot be moved.
    }
    return normalizePetSettings();
  }
}

export function writePetSettings(next: Partial<PetSettings>): PetSettings {
  const current = readPetSettings();
  const normalized = normalizePetSettings({ ...current, ...next });
  fs.mkdirSync(path.dirname(settingsPath()), { recursive: true });
  fs.writeFileSync(settingsPath(), JSON.stringify(normalized, null, 2), 'utf-8');
  return normalized;
}
