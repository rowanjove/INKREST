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
) {
  const displays = screen.getAllDisplays();
  const raw = position;

  if (raw) {
    const matchedDisplay = displays.find((d) => {
      const wa = d.workArea;
      return (
        raw.x >= wa.x &&
        raw.x <= wa.x + wa.width &&
        raw.y >= wa.y &&
        raw.y <= wa.y + wa.height
      );
    });

    if (matchedDisplay) {
      const wa = matchedDisplay.workArea;
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
  return {
    ...DEFAULT_SETTINGS,
    ...input,
    size,
    position: input.position
      ? clampPetPosition(input.position, size)
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
