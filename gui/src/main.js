const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

// Resolve repo root (gui/ is one level below repo root)
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const VENV_PYTHON = path.join(REPO_ROOT, 'venv', 'bin', 'python');
const DAM_CMD = path.join(REPO_ROOT, 'venv', 'bin', 'dam');
const ENV_FILE = path.join(REPO_ROOT, '.env');
const ENV_SAMPLE = path.join(REPO_ROOT, '.env.example');

let mainWindow;
let activeProcess = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 740,
    minWidth: 800,
    minHeight: 600,
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#1a1a1f',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, '..', 'assets', 'icon.png'),
    show: false,
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer.html'));

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// ── IPC: Run a dam command ──────────────────────────────────────────────────

ipcMain.handle('run-dam', (event, args) => {
  return new Promise((resolve, reject) => {
    if (activeProcess) {
      event.sender.send('output', { type: 'warning', text: 'A process is already running.\n' });
      return reject(new Error('Process already running'));
    }

    const cmd = fs.existsSync(DAM_CMD) ? DAM_CMD : null;
    if (!cmd) {
      const msg = 'dam command not found.\nRun: source venv/bin/activate && pip install -e .\n';
      event.sender.send('output', { type: 'error', text: msg });
      return reject(new Error('dam not found'));
    }

    event.sender.send('output', { type: 'command', text: `$ dam ${args.join(' ')}\n` });
    event.sender.send('process-start');

    activeProcess = spawn(cmd, args, {
      cwd: REPO_ROOT,
      env: { ...process.env, FORCE_COLOR: '0', NO_COLOR: '1' },
    });

    activeProcess.stdout.on('data', (data) => {
      event.sender.send('output', { type: 'stdout', text: data.toString() });
    });

    activeProcess.stderr.on('data', (data) => {
      event.sender.send('output', { type: 'stderr', text: data.toString() });
    });

    activeProcess.on('close', (code) => {
      activeProcess = null;
      event.sender.send('process-end', { code });
      if (code === 0) resolve({ code });
      else reject(new Error(`Process exited with code ${code}`));
    });

    activeProcess.on('error', (err) => {
      activeProcess = null;
      event.sender.send('output', { type: 'error', text: `Error: ${err.message}\n` });
      event.sender.send('process-end', { code: 1 });
      reject(err);
    });
  });
});

// ── IPC: Kill active process ────────────────────────────────────────────────

ipcMain.handle('kill-process', () => {
  if (activeProcess) {
    activeProcess.kill('SIGTERM');
    activeProcess = null;
    return true;
  }
  return false;
});

// ── IPC: Check venv exists ─────────────────────────────────────────────────

ipcMain.handle('check-venv', () => {
  return {
    venvExists: fs.existsSync(VENV_PYTHON),
    damExists: fs.existsSync(DAM_CMD),
    envExists: fs.existsSync(ENV_FILE),
    repoRoot: REPO_ROOT,
  };
});

// ── IPC: Read .env file ─────────────────────────────────────────────────────

ipcMain.handle('read-env', () => {
  const source = fs.existsSync(ENV_FILE) ? ENV_FILE : ENV_SAMPLE;
  if (!fs.existsSync(source)) return {};
  const lines = fs.readFileSync(source, 'utf8').split('\n');
  const result = {};
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const idx = trimmed.indexOf('=');
    if (idx < 0) continue;
    const key = trimmed.slice(0, idx).trim();
    const value = trimmed.slice(idx + 1).trim().replace(/^["']|["']$/g, '');
    result[key] = value;
  }
  return result;
});

// ── IPC: Write .env file ────────────────────────────────────────────────────

ipcMain.handle('write-env', (event, updates) => {
  let content = fs.existsSync(ENV_FILE)
    ? fs.readFileSync(ENV_FILE, 'utf8')
    : fs.existsSync(ENV_SAMPLE)
    ? fs.readFileSync(ENV_SAMPLE, 'utf8')
    : '';

  for (const [key, value] of Object.entries(updates)) {
    const pattern = new RegExp(`^${key}\\s*=.*$`, 'm');
    const replacement = `${key}="${value}"`;
    if (pattern.test(content)) {
      content = content.replace(pattern, replacement);
    } else {
      if (!content.endsWith('\n')) content += '\n';
      content += `${replacement}\n`;
    }
  }

  fs.writeFileSync(ENV_FILE, content, 'utf8');
  return true;
});

// ── IPC: Pick a folder ─────────────────────────────────────────────────────

ipcMain.handle('pick-folder', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Select Library Root',
  });
  return result.canceled ? null : result.filePaths[0];
});

// ── IPC: Open URL in browser ───────────────────────────────────────────────

ipcMain.handle('open-url', (event, url) => {
  shell.openExternal(url);
});
