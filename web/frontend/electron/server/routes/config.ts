import { Router } from 'express';
import fs from 'fs';
import path from 'path';
import yaml from 'yaml';

export const configRouter = Router();

function getDataDir(): string {
  return process.env.NOVEL_AGENT_ROOT || path.join(process.cwd(), '..', '..');
}

function getConfigPath(): string {
  return path.join(getDataDir(), 'config', 'pipeline.yaml');
}

const SECRET_KEYS = new Set(['api_key']);
const SECRET_MASK = '********';

function maskSecrets(obj: any): any {
  if (typeof obj !== 'object' || obj === null) return obj;
  const result: any = Array.isArray(obj) ? [] : {};
  for (const [key, value] of Object.entries(obj)) {
    if (SECRET_KEYS.has(key) && typeof value === 'string' && value) {
      result[key] = SECRET_MASK;
    } else if (typeof value === 'object' && value !== null) {
      result[key] = maskSecrets(value);
    } else {
      result[key] = value;
    }
  }
  return result;
}

function mergePreservingSecrets(current: any, incoming: any): any {
  if (typeof current !== 'object' || current === null || typeof incoming !== 'object' || incoming === null) {
    return incoming;
  }
  const result: any = Array.isArray(incoming) ? [] : { ...current };
  for (const [key, value] of Object.entries(incoming)) {
    const oldValue = current[key];
    if (SECRET_KEYS.has(key) && (value === SECRET_MASK || value === '' || value === '***' || value === '******')) {
      result[key] = oldValue || '';
    } else if (typeof value === 'object' && value !== null && typeof oldValue === 'object' && oldValue !== null) {
      result[key] = mergePreservingSecrets(oldValue, value);
    } else {
      result[key] = value;
    }
  }
  return result;
}

configRouter.get('/', (_req, res) => {
  const configPath = getConfigPath();
  try {
    if (fs.existsSync(configPath)) {
      const raw = yaml.parse(fs.readFileSync(configPath, 'utf-8')) || {};
      res.json(maskSecrets(raw));
    } else {
      res.json({});
    }
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

configRouter.put('/', (req, res) => {
  const configPath = getConfigPath();
  try {
    let current: any = {};
    if (fs.existsSync(configPath)) {
      current = yaml.parse(fs.readFileSync(configPath, 'utf-8')) || {};
    }

    current = mergePreservingSecrets(current, req.body);

    fs.mkdirSync(path.dirname(configPath), { recursive: true });
    fs.writeFileSync(configPath, yaml.stringify(current, { lineWidth: 0 }), 'utf-8');
    res.json({ status: 'updated' });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});
