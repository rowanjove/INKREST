const { app, BrowserWindow, dialog, shell } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const net = require("net");
const path = require("path");

let mainWindow = null;
let serverProcess = null;

function isDev() {
  return !app.isPackaged;
}

function repoRoot() {
  return path.resolve(__dirname, "..", "..", "..");
}

function resourceRoot() {
  return isDev() ? repoRoot() : path.join(process.resourcesPath, "python");
}

function templateRoot() {
  return isDev() ? repoRoot() : path.join(process.resourcesPath, "templates");
}

function copyDirIfMissing(source, target) {
  if (!fs.existsSync(source) || fs.existsSync(target)) return;
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.cpSync(source, target, { recursive: true });
}

function ensureUserData() {
  const userRoot = path.join(app.getPath("userData"), "project");
  for (const name of ["config", "assets", "state", "prompts"]) {
    copyDirIfMissing(path.join(templateRoot(), name), path.join(userRoot, name));
  }
  for (const name of ["workspace", "dashboard", "data"]) {
    fs.mkdirSync(path.join(userRoot, name), { recursive: true });
  }
  return userRoot;
}

function getFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      const port = typeof address === "object" && address ? address.port : 0;
      server.close(() => resolve(port));
    });
    server.on("error", reject);
  });
}

function waitForServer(url, timeoutMs = 20000) {
  const startedAt = Date.now();
  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const response = await fetch(`${url}/api/health`);
        if (response.ok) {
          resolve();
          return;
        }
      } catch {
        // Server is still starting.
      }
      if (Date.now() - startedAt > timeoutMs) {
        reject(new Error("栖墨后端服务未能及时启动。"));
        return;
      }
      setTimeout(tick, 350);
    };
    tick();
  });
}

async function startBackend() {
  const port = isDev() ? 8000 : await getFreePort();
  const userRoot = ensureUserData();
  const cwd = resourceRoot();
  const pythonCommand = process.env.NOVEL_AGENT_PYTHON || "python";

  serverProcess = spawn(
    pythonCommand,
    ["main.py", "--host", "127.0.0.1", "--port", String(port), "--no-browser"],
    {
      cwd,
      env: {
        ...process.env,
        NOVEL_AGENT_ROOT: userRoot,
        PYTHONIOENCODING: "utf-8",
      },
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    },
  );

  serverProcess.stdout.on("data", (data) => {
    console.log(`[backend] ${data.toString().trim()}`);
  });
  serverProcess.stderr.on("data", (data) => {
    console.error(`[backend] ${data.toString().trim()}`);
  });
  serverProcess.on("exit", (code) => {
    if (code !== 0 && mainWindow) {
      mainWindow.webContents.send("backend-exit", code);
    }
  });

  const backendUrl = `http://127.0.0.1:${port}`;
  await waitForServer(backendUrl);
  return { backendUrl, userRoot };
}

async function createWindow() {
  const { backendUrl, userRoot } = await startBackend();
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 920,
    minWidth: 1180,
    minHeight: 760,
    title: "栖墨 · INKREST",
    backgroundColor: "#f4f1ea",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.maximize();
  mainWindow.removeMenu();
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  if (isDev() && process.env.VITE_DEV_SERVER_URL) {
    await mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
  } else if (isDev()) {
    await mainWindow.loadURL("http://127.0.0.1:5173");
  } else {
    await mainWindow.loadURL(backendUrl);
  }

  mainWindow.webContents.once("did-finish-load", () => {
    mainWindow.webContents.executeJavaScript(
      `window.__NOVEL_AGENT__ = ${JSON.stringify({ backendUrl, userRoot })};`,
    );
  });
}

app.whenReady().then(createWindow).catch((error) => {
  dialog.showErrorBox("栖墨启动失败", error.stack || error.message);
  app.quit();
});

app.on("window-all-closed", () => {
  app.quit();
});

app.on("before-quit", () => {
  if (serverProcess && !serverProcess.killed) {
    serverProcess.kill();
  }
});
