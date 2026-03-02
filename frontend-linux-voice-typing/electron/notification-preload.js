const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods for the notification window
contextBridge.exposeInMainWorld('electronAPI', {
  closeNotification: () => ipcRenderer.invoke('close-notification')
});

