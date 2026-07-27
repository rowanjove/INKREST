import { spawn, ChildProcess, spawnSync } from 'child_process';
import { EventEmitter } from 'events';
import path from 'path';
import fs from 'fs';

function inferStreamLogLevel(text: string): 'info' | 'warn' | 'error' {
  const line = text.trim();
  if (!line) return 'info';
  if (/\b(CRITICAL|FATAL|Traceback|Exception)\b/i.test(line)) return 'error';
  if (/\b(ERROR|Failed|失败)\b/i.test(line) && !/\bINFO\b/i.test(line)) return 'error';
  if (/\b(WARNING|WARN|警告)\b/i.test(line)) return 'warn';
  if (/\b(INFO|DEBUG|TRACE|Started server|Uvicorn running|Application startup)\b/i.test(line)) {
    return 'info';
  }
  return 'info';
}

export class PythonBridge extends EventEmitter {
  private process: ChildProcess | null = null;
  private serverProcess: ChildProcess | null = null;
  private codeDir: string;
  private dataDir: string;
  private templatesDir: string;
  private pythonCmd: string;
  private backendExe: string | null;

  constructor(dataDir?: string) {
    super();
    this.codeDir = this.resolveCodeDir();
    this.dataDir = dataDir || process.env.NOVEL_AGENT_ROOT || this.codeDir;
    this.templatesDir = this.resolveTemplatesDir();
    this.backendExe = this.resolveBackendExe();
    this.pythonCmd = this.resolvePython();
  }

  private resolveCodeDir(): string {
    const packagedDir = path.join(process.resourcesPath || '', 'python');
    if (fs.existsSync(path.join(packagedDir, 'main.py'))) return packagedDir;
    return path.resolve(process.cwd(), '..', '..');
  }

  private resolveBackendExe(): string | null {
    const runtimeDir = path.join(process.resourcesPath || '', 'python-runtime');
    const candidates = [
      path.join(runtimeDir, 'novel-agent-backend.exe'),
      path.join(runtimeDir, 'novel-agent-backend', 'novel-agent-backend.exe'),
    ];
    return candidates.find(candidate => fs.existsSync(candidate)) || null;
  }

  private resolveTemplatesDir(): string {
    const packagedTemplates = path.join(process.resourcesPath || '', 'templates');
    if (fs.existsSync(packagedTemplates)) return packagedTemplates;
    return this.codeDir;
  }

  private resolvePython(): string {
    // Check for embedded Python first (packaged mode)
    const embeddedPath = path.join(process.resourcesPath || '', 'python-runtime', 'python.exe');
    if (fs.existsSync(embeddedPath)) return embeddedPath;

    // Check for system Python
    const candidates = ['python', 'python3', 'py'];
    for (const cmd of candidates) {
      const result = spawnSync(cmd, ['--version'], { shell: false, stdio: 'ignore' });
      if (result.status === 0) {
        return cmd;
      }
    }

    return 'python';
  }

  private commandArgs(args: string[]): { command: string; args: string[]; cwd: string } {
    if (this.backendExe) {
      return {
        command: this.backendExe,
        args,
        cwd: path.dirname(this.backendExe),
      };
    }
    return {
      command: this.pythonCmd,
      args: ['-m', 'main', ...args],
      cwd: this.codeDir,
    };
  }

  async startServer(port: number = 8000): Promise<void> {
    if (this.serverProcess && !this.serverProcess.killed) return;

    const command = this.commandArgs([
      'serve',
      '--host', '127.0.0.1',
      '--port', String(port),
      '--no-browser',
      '--root-dir', this.dataDir,
    ]);

    this.serverProcess = spawn(command.command, command.args, {
      cwd: command.cwd,
      env: {
        ...process.env,
        NOVEL_AGENT_ROOT: this.dataDir,
        NOVEL_AGENT_TEMPLATES: this.templatesDir,
        PYTHONIOENCODING: 'utf-8',
        PYTHONUNBUFFERED: '1',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    this.serverProcess.stdout?.on('data', (data: Buffer) => {
      this.emit('log', { type: 'log', message: data.toString('utf-8').trim(), level: 'info' });
    });
    this.serverProcess.stderr?.on('data', (data: Buffer) => {
      const message = data.toString('utf-8').trim();
      if (!message) return;
      this.emit('log', { type: 'log', message, level: inferStreamLogLevel(message) });
    });
    this.serverProcess.on('error', (err) => {
      this.emit('error', { type: 'error', error: err.message });
    });

    await this.waitForServer(port);
  }

  private async waitForServer(port: number): Promise<void> {
    const deadline = Date.now() + 60000;
    while (Date.now() < deadline) {
      try {
        const response = await fetch(`http://127.0.0.1:${port}/api/health`);
        if (response.ok) return;
      } catch {
        // Server is still starting.
      }
      await new Promise(resolve => setTimeout(resolve, 300));
    }
    throw new Error(`Python server did not start on port ${port}`);
  }

  abort(): void {
    if (this.process) {
      const runningProcess = this.process;
      let exited = false;
      runningProcess.once('exit', () => {
        exited = true;
      });
      runningProcess.kill('SIGTERM');
      setTimeout(() => {
        if (!exited) {
          runningProcess.kill('SIGKILL');
        }
      }, 5000);
      this.process = null;
    }
  }

  stopServer(): void {
    if (this.serverProcess) {
      this.serverProcess.kill('SIGTERM');
      this.serverProcess = null;
    }
  }

  isRunning(): boolean {
    return this.process !== null && !this.process.killed;
  }
}
