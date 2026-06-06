import { Router } from 'express';
import fs from 'fs';
import path from 'path';

export const chaptersRouter = Router();

function getDataDir(): string {
  const userData = process.env.NOVEL_AGENT_ROOT || path.join(process.cwd(), '..', '..');
  return userData;
}

function readJson(filePath: string): any {
  try {
    if (!fs.existsSync(filePath)) return {};
    return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  } catch {
    return {};
  }
}

function readText(filePath: string): string {
  try {
    if (!fs.existsSync(filePath)) return '';
    return fs.readFileSync(filePath, 'utf-8');
  } catch {
    return '';
  }
}

chaptersRouter.get('/', (_req, res) => {
  const chaptersDir = path.join(getDataDir(), 'workspace', 'chapters');
  if (!fs.existsSync(chaptersDir)) return res.json([]);

  const entries = fs.readdirSync(chaptersDir)
    .filter(d => d.startsWith('chapter_'))
    .sort();

  const results = entries.map(entry => {
    const chapterId = entry.replace('chapter_', '');
    const chapterDir = path.join(chaptersDir, entry);
    const plan = readJson(path.join(chapterDir, 'plan.json'));
    const wordcount = readJson(path.join(chapterDir, 'reports', 'wordcount.json'));
    const audit = readJson(path.join(chapterDir, 'reports', 'audit.json'));
    return {
      chapter_id: chapterId,
      title: plan.chapter_title || '',
      word_count: wordcount.count || 0,
      risk_level: audit.risk_level || '',
      final_path: path.join(chapterDir, 'chapter_final.txt'),
    };
  });

  res.json(results);
});

chaptersRouter.get('/tasks', (_req, res) => {
  // Tasks are managed by the Express-side task manager or Python bridge
  // For now return empty; the real tasks come from Python bridge events
  res.json([]);
});

chaptersRouter.get('/:id', (req, res) => {
  const chapterDir = path.join(getDataDir(), 'workspace', 'chapters', `chapter_${req.params.id}`);
  if (!fs.existsSync(chapterDir)) return res.status(404).json({ error: 'Chapter not found' });

  const plan = readJson(path.join(chapterDir, 'plan.json'));
  const wordcount = readJson(path.join(chapterDir, 'reports', 'wordcount.json'));
  const audit = readJson(path.join(chapterDir, 'reports', 'audit.json'));
  const continuity = readJson(path.join(chapterDir, 'reports', 'continuity.json'));
  const stateUpdate = readJson(path.join(chapterDir, 'state_update.json'));

  res.json({
    chapter_id: req.params.id,
    title: plan.chapter_title || '',
    final_text: readText(path.join(chapterDir, 'chapter_final.txt')),
    plan,
    wordcount,
    audit,
    continuity,
    state_update: stateUpdate,
    chapter_summary: readText(path.join(chapterDir, 'chapter_summary.md')),
  });
});

chaptersRouter.post('/run', async (req, res) => {
  const { chapter_id, goal, dry_run } = req.body;
  if (!chapter_id || !goal) {
    return res.status(400).json({ error: 'chapter_id and goal are required' });
  }

  // This will be handled by Python bridge via IPC
  // For now, respond with task accepted
  const taskId = `task_${Date.now()}`;
  res.json({ task_id: taskId, chapter_id, status: 'pending' });
});
