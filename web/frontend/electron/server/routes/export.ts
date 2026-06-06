import { Router } from 'express';
import fs from 'fs';
import path from 'path';
import { spawnSync } from 'child_process';
import os from 'os';

export const exportRouter = Router();

function getDataDir(): string {
  return process.env.NOVEL_AGENT_ROOT || path.join(process.cwd(), '..', '..');
}

exportRouter.post('/', (req, res) => {
  const { format, title, chapter_ids } = req.query as {
    format?: string;
    title?: string;
    chapter_ids?: string;
  };

  if (!format || !['txt', 'epub', 'pdf'].includes(format)) {
    return res.status(400).json({ error: 'Invalid format. Use txt, epub, or pdf.' });
  }

  const rootDir = getDataDir();
  const tmpFile = path.join(os.tmpdir(), `novel_export_${Date.now()}.${format}`);

  try {
    // Call Python exporter via subprocess
    const args = [
      '-m',
      'novel_agent.exporters.cli',
      '--format',
      format,
      '--root-dir',
      rootDir,
      '--output',
      tmpFile,
    ];
    if (chapter_ids) args.push('--chapter-ids', chapter_ids);
    if (title) args.push('--title', title);

    const result = spawnSync('python', args, {
      cwd: rootDir,
      encoding: 'utf-8',
      shell: false,
      timeout: 60000,
    });
    if (result.error) throw result.error;
    if (result.status !== 0) {
      throw new Error(result.stderr || result.stdout || `Exporter exited with ${result.status}`);
    }

    if (!fs.existsSync(tmpFile)) {
      return res.status(500).json({ error: 'Export produced no output file' });
    }

    const filename = `${title || 'novel'}.${format}`;
    res.download(tmpFile, filename, (err) => {
      // Clean up temp file
      try { fs.unlinkSync(tmpFile); } catch { /* ignore */ }
      if (err && !res.headersSent) {
        res.status(500).json({ error: err.message });
      }
    });
  } catch (err: any) {
    try { fs.unlinkSync(tmpFile); } catch { /* ignore */ }
    res.status(500).json({ error: `Export failed: ${err.message}` });
  }
});
