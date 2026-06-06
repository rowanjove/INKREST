import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

let db: Database.Database | null = null;

function getDataDir(): string {
  return process.env.NOVEL_AGENT_ROOT || path.join(process.cwd(), '..', '..');
}

export function getDatabase(): Database.Database {
  if (db) return db;

  const dbDir = path.join(getDataDir(), 'data');
  fs.mkdirSync(dbDir, { recursive: true });

  const dbPath = path.join(dbDir, 'novel.sqlite');
  db = new Database(dbPath);

  // Enable WAL mode for concurrent reads
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');

  initSchema(db);
  return db;
}

function initSchema(db: Database.Database) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS character_state (
      id TEXT PRIMARY KEY,
      name TEXT,
      location TEXT,
      emotion TEXT,
      payload TEXT
    );

    CREATE TABLE IF NOT EXISTS chapters (
      id TEXT PRIMARY KEY,
      title TEXT,
      final_path TEXT,
      word_count INTEGER,
      risk_level TEXT
    );

    CREATE TABLE IF NOT EXISTS chapter_summaries (
      chapter_id TEXT PRIMARY KEY,
      summary TEXT,
      summary_path TEXT
    );

    CREATE TABLE IF NOT EXISTS events (
      id TEXT PRIMARY KEY,
      chapter_id TEXT,
      scene_id TEXT,
      characters TEXT,
      objects TEXT,
      summary TEXT,
      threads TEXT,
      payload TEXT
    );

    CREATE TABLE IF NOT EXISTS timeline_nodes (
      id TEXT PRIMARY KEY,
      type TEXT,
      name TEXT,
      description TEXT,
      status TEXT,
      chapter_id TEXT,
      payload TEXT
    );

    CREATE TABLE IF NOT EXISTS timeline_edges (
      id TEXT PRIMARY KEY,
      from_node TEXT,
      to_node TEXT,
      type TEXT,
      description TEXT,
      strength TEXT,
      change TEXT,
      chapter_id TEXT,
      payload TEXT
    );

    CREATE TABLE IF NOT EXISTS foreshadows (
      id TEXT PRIMARY KEY,
      title TEXT,
      status TEXT DEFAULT 'open',
      description TEXT,
      chapter_id TEXT,
      payload TEXT
    );

    CREATE TABLE IF NOT EXISTS hooks (
      id TEXT PRIMARY KEY,
      title TEXT,
      status TEXT DEFAULT 'open',
      description TEXT,
      chapter_id TEXT,
      payload TEXT
    );

    CREATE TABLE IF NOT EXISTS objects (
      id TEXT PRIMARY KEY,
      name TEXT,
      holder TEXT,
      status TEXT,
      payload TEXT
    );

    CREATE TABLE IF NOT EXISTS threads (
      id TEXT PRIMARY KEY,
      title TEXT,
      status TEXT DEFAULT 'open',
      summary TEXT,
      payload TEXT
    );
  `);
}

export function closeDatabase() {
  if (db) {
    db.close();
    db = null;
  }
}
