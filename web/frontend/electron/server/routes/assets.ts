import { Router } from 'express';
import fs from 'fs';
import path from 'path';

export const assetsRouter = Router();

const ASSET_FILES: Record<string, string> = {
  character_cards: 'assets/character_cards.yaml',
  world_bible: 'assets/world_bible.md',
  style_guide: 'assets/style_guide.md',
  rules: 'assets/rules.yaml',
};

const CONFIG_ASSET_FILES: Record<string, string> = {
  sensitive_words: 'assets/sensitive_words.txt',
};

const ALL_ASSET_FILES: Record<string, string> = {
  ...ASSET_FILES,
  ...CONFIG_ASSET_FILES,
};

function getDataDir(): string {
  return process.env.NOVEL_AGENT_ROOT || path.join(process.cwd(), '..', '..');
}

assetsRouter.get('/', (_req, res) => {
  const rootDir = getDataDir();
  const results = Object.entries(ASSET_FILES).map(([name, relPath]) => {
    const fullPath = path.join(rootDir, relPath);
    const exists = fs.existsSync(fullPath);
    return {
      name,
      path: relPath,
      exists,
      size: exists ? fs.statSync(fullPath).size : 0,
    };
  });
  res.json(results);
});

assetsRouter.get('/:name', (req, res) => {
  const relPath = ALL_ASSET_FILES[req.params.name];
  if (!relPath) return res.status(404).json({ error: 'Asset not found' });

  const fullPath = path.join(getDataDir(), relPath);
  let content = '';
  try {
    if (fs.existsSync(fullPath)) content = fs.readFileSync(fullPath, 'utf-8');
  } catch { /* empty */ }

  res.json({ name: req.params.name, path: relPath, content });
});

assetsRouter.put('/:name', (req, res) => {
  const relPath = ALL_ASSET_FILES[req.params.name];
  if (!relPath) return res.status(404).json({ error: 'Asset not found' });

  const fullPath = path.join(getDataDir(), relPath);
  fs.mkdirSync(path.dirname(fullPath), { recursive: true });
  fs.writeFileSync(fullPath, req.body.content || '', 'utf-8');
  res.json({ name: req.params.name, status: 'updated' });
});
