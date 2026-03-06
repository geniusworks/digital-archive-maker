const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('dam', {
  // Run a dam subcommand; streams output via onOutput callback
  run: (args) => ipcRenderer.invoke('run-dam', args),
  kill: () => ipcRenderer.invoke('kill-process'),

  // Environment status
  checkVenv: () => ipcRenderer.invoke('check-venv'),

  // .env file management
  readEnv: () => ipcRenderer.invoke('read-env'),
  writeEnv: (updates) => ipcRenderer.invoke('write-env', updates),

  // Native dialogs
  pickFolder: () => ipcRenderer.invoke('pick-folder'),
  openUrl: (url) => ipcRenderer.invoke('open-url', url),

  // Event listeners
  onOutput: (cb) => ipcRenderer.on('output', (_, data) => cb(data)),
  onProcessStart: (cb) => ipcRenderer.on('process-start', () => cb()),
  onProcessEnd: (cb) => ipcRenderer.on('process-end', (_, data) => cb(data)),
  removeAllListeners: (channel) => ipcRenderer.removeAllListeners(channel),
});
