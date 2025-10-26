const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Platform information
  platform: process.platform,
  versions: process.versions,

  // Window management
  setWindowSize: (size) => ipcRenderer.invoke('set-window-size', size),
  getScreenSize: () => ipcRenderer.invoke('get-screen-size'),
  setAlwaysOnTop: (flag) => ipcRenderer.invoke('set-always-on-top', flag),
  hideWindow: () => ipcRenderer.invoke('hide-window'),
  showWindow: () => ipcRenderer.invoke('show-window'),
  quitApp: () => ipcRenderer.invoke('quit-app'),

  // Gateway client functionality
  connectGateway: () => ipcRenderer.invoke('connect-gateway'),
  disconnectGateway: () => ipcRenderer.invoke('disconnect-gateway'),
  sendAudioData: (audioData, sampleRate) => ipcRenderer.invoke('send-audio-data', audioData, sampleRate),
  // Fast, fire-and-forget streaming channel
  sendAudioChunk: (audioData, sampleRate) => ipcRenderer.send('audio-chunk', audioData, sampleRate),
  updateLanguages: (sourceLang, targetLang) => ipcRenderer.invoke('update-languages', sourceLang, targetLang),
  sendStartOver: () => ipcRenderer.invoke('send-start-over'),
  getConnectionStatus: () => ipcRenderer.invoke('get-connection-status'),

  // Mode switching
  setMode: (mode) => ipcRenderer.invoke('set-mode', mode),
  getMode: () => ipcRenderer.invoke('get-mode'),

  // Notification functions
  showNotification: (title, message) => ipcRenderer.invoke('show-notification', title, message),

  // Event listeners for gateway messages
  onConnectionStatus: (callback) => ipcRenderer.on('connection-status', callback),
  onRealtimeResult: (callback) => ipcRenderer.on('realtime-result', callback),
  onUtteranceEnd: (callback) => ipcRenderer.on('utterance-end', callback),
  onLiveTranscriptionUpdate: (callback) => ipcRenderer.on('live-transcription-update', callback),

  // Global shortcut event listener
  onGlobalShortcut: (callback) => ipcRenderer.on('global-shortcut', callback),

  // Remove listeners
  removeAllListeners: (event) => ipcRenderer.removeAllListeners(event),

  // Subtitle overlay controls
  showSubtitle: () => ipcRenderer.invoke('subtitle-show'),
  hideSubtitle: () => ipcRenderer.invoke('subtitle-hide'),
  updateSubtitle: (text) => ipcRenderer.send('subtitle-text', text),
  updateDualSubtitle: (data) => ipcRenderer.send('subtitle-text-dual', data)
});
