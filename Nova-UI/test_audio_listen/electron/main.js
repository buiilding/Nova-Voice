const path = require('path');
const { app, BrowserWindow, session } = require('electron');

const isDev = process.env.NODE_ENV === 'development';

function createMainWindow() {
  const mainWindow = new BrowserWindow({
    width: 1000,
    height: 700,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
  }

  return mainWindow;
}

function setupPermissionHandlers() {
  const ses = session.defaultSession;

  // Grant media (mic) permissions within the app. OS-level prompts may still appear once.
  ses.setPermissionRequestHandler((webContents, permission, callback) => {
    if (permission === 'media' || permission === 'display-capture') {
      callback(true);
      return;
    }
    callback(false);
  });

  // Auto-approve display media with system audio loopback (Windows). This satisfies getDisplayMedia.
  if (typeof ses.setDisplayMediaRequestHandler === 'function') {
    ses.setDisplayMediaRequestHandler((request, callback) => {
      // Choose the first screen as the source; include loopback audio when available (Windows)
      const { desktopCapturer } = require('electron');
      desktopCapturer.getSources({ types: ['screen'] }).then((sources) => {
        const primary = sources[0];
        if (!primary) {
          callback({ video: null, audio: 'none' });
          return;
        }
        callback({
          video: primary,
          audio: 'loopback' // On macOS/Linux this will be ignored; Windows supports system audio
        });
      }).catch(() => {
        callback({ video: null, audio: 'none' });
      });
    });
  }
}

app.whenReady().then(() => {
  setupPermissionHandlers();
  createMainWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createMainWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});


