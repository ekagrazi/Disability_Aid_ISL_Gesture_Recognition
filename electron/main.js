const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn, execSync } = require('child_process');

// Determine if running in development mode
const isDev = !app.isPackaged;

let mainWindow;
let backendProcess = null;

// ── Python Backend Spawning ──────────────────────────────────────────────────

function spawnBackend() {
  if (isDev) {
    // Development: run python directly from source
    const projectRoot = path.join(__dirname, '..');
    backendProcess = spawn('python', ['backend/main.py'], {
      cwd: projectRoot,
      stdio: 'pipe',
    });
  } else {
    // Production: run the PyInstaller-compiled executable from resources
    const exePath = path.join(process.resourcesPath, 'backend', 'backend.exe');
    backendProcess = spawn(exePath, [], {
      stdio: 'pipe',
    });
  }

  backendProcess.stdout.on('data', (data) => {
    console.log(`[backend] ${data}`);
  });

  backendProcess.stderr.on('data', (data) => {
    console.error(`[backend] ${data}`);
  });

  backendProcess.on('error', (err) => {
    console.error('[backend] Failed to start:', err.message);
  });

  backendProcess.on('exit', (code) => {
    console.log(`[backend] Exited with code ${code}`);
    backendProcess = null;
  });
}

function killBackend() {
  if (!backendProcess) return;

  const pid = backendProcess.pid;
  console.log(`[backend] Killing process tree (PID: ${pid})`);

  try {
    // On Windows, use taskkill to kill the entire process tree
    // (uvicorn may spawn sub-processes)
    if (process.platform === 'win32') {
      execSync(`taskkill /PID ${pid} /T /F`, { stdio: 'ignore' });
    } else {
      backendProcess.kill('SIGTERM');
    }
  } catch (err) {
    // Process may already be dead — that's fine
    console.warn('[backend] Kill error (likely already exited):', err.message);
  }

  backendProcess = null;
}

// ── Window Creation ──────────────────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 720,
    frame: false, // Frameless window
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  if (isDev) {
    // In development, load from the React dev server
    mainWindow.loadURL('http://localhost:3000');
  } else {
    // In production, load the built React app (Vite outputs to dist/)
    mainWindow.loadFile(path.join(__dirname, '..', 'frontend', 'dist', 'index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ── IPC Handlers ──────────────────────────────────────────────────────────────

ipcMain.on('window-minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.on('window-close', () => {
  if (mainWindow) mainWindow.close();
});

// ── App Lifecycle ─────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  spawnBackend();
  createWindow();
});

app.on('before-quit', () => {
  killBackend();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
