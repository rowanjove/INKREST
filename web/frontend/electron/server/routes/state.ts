import { Router } from 'express';
import path from 'path';
import Database from 'better-sqlite3';

export const stateRouter = Router();

function getDb(): Database.Database | null {
  const rootDir = process.env.NOVEL_AGENT_ROOT || path.join(process.cwd(), '..', '..');
  const dbPath = path.join(rootDir, 'data', 'novel.sqlite');
  try {
    if (require('fs').existsSync(dbPath)) {
      return new Database(dbPath, { readonly: true });
    }
  } catch { /* no db yet */ }
  return null;
}

stateRouter.get('/', (_req, res) => {
  const db = getDb();
  if (!db) {
    return res.json({
      characters: {},
      foreshadows: [],
      hooks: [],
      objects: [],
      events: [],
      threads: [],
    });
  }

  try {
    const characters: Record<string, any> = {};
    for (const row of db.prepare('SELECT * FROM character_state').all() as any[]) {
      characters[row.name || row.id] = row;
    }

    const foreshadows = db.prepare('SELECT * FROM foreshadows ORDER BY chapter_id DESC').all();
    const hooks = db.prepare('SELECT * FROM hooks ORDER BY chapter_id DESC').all();
    const objects = db.prepare('SELECT * FROM objects ORDER BY id DESC').all();
    const events = db.prepare('SELECT * FROM events ORDER BY chapter_id DESC LIMIT 100').all();
    const threads = db.prepare('SELECT * FROM threads ORDER BY id DESC').all();

    res.json({ characters, foreshadows, hooks, objects, events, threads });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  } finally {
    db.close();
  }
});

stateRouter.get('/timeline', (_req, res) => {
  const db = getDb();
  if (!db) return res.json({ nodes: [], edges: [], foreshadows: [], hooks: [] });

  try {
    const nodes = db.prepare('SELECT * FROM timeline_nodes ORDER BY chapter_id DESC').all();
    const edges = db.prepare('SELECT * FROM timeline_edges').all();
    const foreshadows = db.prepare('SELECT * FROM foreshadows').all();
    const hooks = db.prepare('SELECT * FROM hooks').all();

    res.json({ nodes, edges, foreshadows, hooks });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  } finally {
    db.close();
  }
});

stateRouter.get('/events', (req, res) => {
  const db = getDb();
  if (!db) return res.json([]);

  const query = (req.query.query as string) || '';
  const limit = parseInt(req.query.limit as string) || 20;

  try {
    let rows;
    if (query) {
      rows = db.prepare(
        'SELECT * FROM events WHERE summary LIKE ? ORDER BY chapter_id DESC LIMIT ?'
      ).all(`%${query}%`, limit);
    } else {
      rows = db.prepare(
        'SELECT * FROM events ORDER BY chapter_id DESC LIMIT ?'
      ).all(limit);
    }
    res.json(rows);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  } finally {
    db.close();
  }
});
