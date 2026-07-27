import { spawn, ChildProcess, spawnSync } from 'child_process';
import { EventEmitter } from 'events';
import path from 'path';
import fs from 'fs';

export interface PythonBridgeDependencies {
  spawnProcess?: typeof spawn;
  fetchHealth?: typeof fetch;
  pythonCommand?: string;
}

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
  private readonly spawnProcess: typeof spawn;
  private readonly fetchHealth: typeof fetch;
  private startPromise: Promise<void> | null = null;
  private stopPromise: Promise<void> | null = null;
  private serverPort: number | null = null;

  constructor(dataDir?: string, dependencies: PythonBridgeDependencies = {}) {
    super();
    this.spawnProcess = dependencies.spawnProcess || spawn;
    this.fetchHealth = dependencies.fetchHealth || fetch;
    this.codeDir = this.resolveCodeDir();
    this.dataDir = dataDir || process.env.NOVEL_AGENT_ROOT || this.codeDir;
    this.templatesDir = this.resolveTemplatesDir();
    this.backendExe = this.resolveBackendExe();
    this.pythonCmd = dependencies.pythonCommand || this.resolvePython();
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
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
      throw new RangeError('port must be a valid TCP port');
    }
    if (this.stopPromise) await this.stopPromise;
    if (
      this.serverProcess
      && this.serverProcess.exitCode === null
      && !this.serverProcess.killed
    ) {
      if (this.serverPort !== port) {
        throw new Error(`Python server is already running on port ${this.serverPort}`);
      }
      if (this.startPromise) await this.startPromise;
      return;
    }
    if (this.startPromise) return this.startPromise;

    const operation = this.launchServer(port);
    this.startPromise = operation;
    try {
      await operation;
    } finally {
      if (this.startPromise === operation) this.startPromise = null;
    }
  }

  private async launchServer(port: number): Promise<void> {
    const command = this.commandArgs([
      'serve',
      '--host', '127.0.0.1',
      '--port', String(port),
      '--no-browser',
      '--root-dir', this.dataDir,
    ]);

    const child = this.spawnProcess(command.command, command.args, {
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
    this.serverProcess = child;
    this.serverPort = port;

    child.stdout?.on('data', (data: Buffer) => {
      this.emit('log', { type: 'log', message: data.toString('utf-8').trim(), level: 'info' });
    });
    child.stderr?.on('data', (data: Buffer) => {
      const message = data.toString('utf-8').trim();
      if (!message) return;
      this.emit('log', { type: 'log', message, level: inferStreamLogLevel(message) });
    });
    child.on('error', (err) => {
      this.emit('error', { type: 'error', error: err.message });
    });
    child.once('exit', () => {
      if (this.serverProcess === child) {
        this.serverProcess = null;
        this.serverPort = null;
      }
    });

    try {
      await this.waitForServer(port, child);
    } catch (error) {
      if (!child.killed && child.exitCode === null) {
        await this.terminateChild(child);
      }
      throw error;
    }
  }

  private async waitForServer(port: number, child: ChildProcess): Promise<void> {
    const deadline = Date.now() + 60000;
    while (Date.now() < deadline) {
      if (
        this.serverProcess !== child
        || child.killed
        || child.exitCode !== null
      ) {
        throw new Error('Python server stopped before becoming healthy');
      }
      try {
        const response = await this.fetchHealth(`http://127.0.0.1:${port}/api/health`);
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

  async stopServer(): Promise<void> {
    if (this.stopPromise) return this.stopPromise;
    const operation = this.stopServerProcess();
    this.stopPromise = operation;
    try {
      await operation;
    } finally {
      if (this.stopPromise === operation) this.stopPromise = null;
    }
  }

  private async stopServerProcess(): Promise<void> {
    const pendingStart = this.startPromise;
    const child = this.serverProcess;
    if (child) {
      await this.terminateChild(child);
      if (this.serverProcess === child) {
        this.serverProcess = null;
        this.serverPort = null;
      }
    }
    if (pendingStart) {
      try {
        await pendingStart;
      } catch {
        // Stopping an in-flight start intentionally rejects readiness.
      }
    }
  }

  private async terminateChild(child: ChildProcess): Promise<void> {
    if (child.exitCode !== null) return;
    await new Promise<void>((resolve) => {
      let settled = false;
      let forceTimer: NodeJS.Timeout | null = null;
      let finalTimer: NodeJS.Timeout | null = null;
      const finish = () => {
        if (settled) return;
        settled = true;
        if (forceTimer) clearTimeout(forceTimer);
        if (finalTimer) clearTimeout(finalTimer);
        resolve();
      };
      child.once('exit', finish);
      child.once('error', finish);
      try {
        child.kill('SIGTERM');
      } catch {
        finish();
        return;
      }
      if (child.exitCode !== null) {
        finish();
        return;
      }
      forceTimer = setTimeout(() => {
        if (settled) return;
        try {
          child.kill('SIGKILL');
        } catch {
          finish();
          return;
        }
        finalTimer = setTimeout(finish, 2000);
      }, 5000);
    });
  }

  isServerRunning(): boolean {
    return Boolean(
      this.serverProcess
      && this.serverProcess.exitCode === null
      && !this.serverProcess.killed,
    );
  }

  isRunning(): boolean {
    return this.process !== null && !this.process.killed;
  }
}
