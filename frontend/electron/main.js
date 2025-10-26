// Simplified Electron main process for open-source version
const { app, BrowserWindow, screen, protocol, ipcMain, session, clipboard, globalShortcut } = require('electron');
const { pathToFileURL } = require('url');
const path = require('path');
const WebSocket = require('ws');
const robot = require('robotjs');

// Helper function to get correct preload script path in both dev and packaged mode
function getPreloadPath(scriptName) {
  // __dirname works in both development and packaged mode because
  // Electron automatically handles ASAR paths
  const preloadPath = path.join(__dirname, scriptName);
  console.log(`[PRELOAD] Resolved path for ${scriptName}: ${preloadPath}`);
  console.log(`[PRELOAD] File exists: ${require('fs').existsSync(preloadPath)}`);
  return preloadPath;
}

// Load environment variables from .env file if it exists
try {
  require('dotenv').config();
} catch (error) {
  console.log('[DEBUG] No .env file found, using defaults');
}

// Suppress VA-API/Vulkan warnings on systems without drivers while keeping GPU compositing for transparency
app.commandLine.appendSwitch('disable-accelerated-video-decode');
app.commandLine.appendSwitch('disable-accelerated-video-encode');
app.commandLine.appendSwitch('disable-gpu-memory-buffer-video-frames');

// Enable Windows system audio capture
app.commandLine.appendSwitch('enable-features', 'SystemAudioCapture');
app.commandLine.appendSwitch('allow-running-insecure-content');
app.commandLine.appendSwitch('disable-web-security');
// Combine disable-features into one switch
app.commandLine.appendSwitch('disable-features', 'Vulkan,VaapiVideoDecoder,VaapiVideoEncoder,UseChromeOSDirectVideoDecoder,VizDisplayCompositor');

let mainWindow;
let notificationWindow = null;
let subtitleWindow = null;
let ws = null;
let isConnected = false;
let currentMode = 'typing'; // 'typing' or 'subtitle'
let clientId = null;
let pingInterval = null;

// Client configuration - defaults to localhost for open-source
const GATEWAY_URL = process.env.GATEWAY_URL || 'ws://localhost:8081';
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';

console.log('[CONFIG] GATEWAY_URL:', GATEWAY_URL);
console.log('[CONFIG] BACKEND_URL:', BACKEND_URL);

function createNotificationWindow() {
  if (notificationWindow && !notificationWindow.isDestroyed()) {
    return notificationWindow;
  }

  // Get the primary display's work area size
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

  notificationWindow = new BrowserWindow({
    width: 400,
    height: 120,
    x: Math.floor((screenWidth - 400) / 2),
    y: Math.floor(screenHeight / 3), // Position in upper third of screen
    transparent: true,
    backgroundColor: '#00000000',
    frame: false,
    alwaysOnTop: true,
    resizable: false,
    show: false, // Don't show initially
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'notification-preload.js')
    }
  });

  // Load a simple HTML for the notification
  const notificationHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <style>
        body {
          margin: 0;
          padding: 0;
          background: transparent;
          font-family: Arial, sans-serif;
          overflow: hidden;
        }
        .notification {
          position: relative;
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          opacity: 0;
          transition: opacity 0.5s ease-in-out;
        }
        .notification.show {
          opacity: 1;
        }
        .notification.hide {
          opacity: 0;
        }
        .content {
          background: rgba(15, 23, 42, 0.95);
          border: 1px solid rgba(51, 65, 85, 0.5);
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
          display: flex;
          align-items: center;
          gap: 16px;
          backdrop-filter: blur(10px);
          color: white;
        }
        .icon {
          width: 32px;
          height: 32px;
          background: rgba(51, 65, 85, 0.8);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .text-content {
          flex: 1;
        }
        .title {
          font-weight: bold;
          font-size: 16px;
          margin-bottom: 4px;
        }
        .message {
          font-size: 14px;
          opacity: 0.9;
        }
      </style>
    </head>
    <body>
      <div id="notification" class="notification">
        <div class="content">
          <div class="icon">⚠</div>
          <div class="text-content">
            <div class="title" id="title">Connection Failed</div>
            <div class="message" id="message">Cannot connect to gateway. Make sure the gateway service is running.</div>
          </div>
        </div>
      </div>

      <script>
        const notification = document.getElementById('notification');
        const titleEl = document.getElementById('title');
        const messageEl = document.getElementById('message');

        window.showNotification = (title, message) => {
          titleEl.textContent = title;
          messageEl.textContent = message;
          notification.className = 'notification show';
        };

        window.hideNotification = () => {
          notification.className = 'notification hide';
          setTimeout(() => {
            if (window.electronAPI) {
              window.electronAPI.closeNotification();
            }
          }, 500); // Wait for fade out animation
        };

        // Auto-hide after 2 seconds
        setTimeout(() => {
          if (notification.className.includes('show')) {
            window.hideNotification();
          }
        }, 3000);
      </script>
    </body>
    </html>
  `;

  notificationWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(notificationHtml)}`);

  notificationWindow.on('closed', () => {
    notificationWindow = null;
  });

  return notificationWindow;
}

function showNotification(title = 'Connection Failed', message = 'Cannot connect to gateway. Make sure the gateway service is running.') {
  const win = createNotificationWindow();
  win.webContents.executeJavaScript(`window.showNotification("${title}", "${message}")`);
  win.show();
}

function hideNotification() {
  if (notificationWindow && !notificationWindow.isDestroyed()) {
    notificationWindow.webContents.executeJavaScript('window.hideNotification()');
  }
}

function createWindow() {
  // Get the primary display's work area size
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.workAreaSize;

  // Create the browser window with minimal initial size for Cluely-style approach
  mainWindow = new BrowserWindow({
    width: 100,               // Start small, will resize dynamically
    height: 100,
    x: (width - 100) / 2,     // Center horizontally initially
    y: 0,                     // Position at the top of the screen
    transparent: true,
    backgroundColor: '#00000000',
    frame: false,             // Completely frameless
    alwaysOnTop: true,
    resizable: false,         // Prevent manual resizing
    skipTaskbar: true,        // Hide from taskbar and Alt+Tab
    useContentSize: true,
    autoHideMenuBar: true,
    show: false,              // Don't show until content is measured
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
      enableRemoteModule: false,
      preload: getPreloadPath('preload.js'),
      // Enable system audio capture
      webSecurity: false,
      allowRunningInsecureContent: true,
      experimentalFeatures: true,
      // Enable permissions for audio capture
      permissions: [
        'microphone',
        'media',
        'display-capture'
      ]
    },
    icon: path.join(__dirname, '../public/favicon3-large.png'),
    titleBarStyle: 'hidden',
    titleBarOverlay: false
  });

  // Optional devtools for debugging when ELECTRON_DEBUG=1
  if (process.env.ELECTRON_DEBUG === '1') {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }

  // Load the app from static export using file URL to handle absolute paths
  const htmlPath = path.join(__dirname, '../out/index.html');
  mainWindow.loadURL(pathToFileURL(htmlPath).href);

  // Handle window close
  mainWindow.on('closed', () => {
    console.log('[MAIN WINDOW] Main window closed');
    // Since there's no authentication, just quit the app
    console.log('[MAIN WINDOW] Quitting app due to main window close');
    app.quit();
  });

  // Debug: Log when content is ready
  mainWindow.webContents.on('dom-ready', () => {
    console.log('[DEBUG] Main window DOM ready');
  });

  mainWindow.on('ready-to-show', () => {
    console.log('[DEBUG] Main window ready to show');
  });

  // Make window draggable
  mainWindow.setMovable(true);
}


function createSubtitleWindow() {
  if (subtitleWindow && !subtitleWindow.isDestroyed()) {
    return subtitleWindow;
  }

  console.log('[SUBTITLE] Creating subtitle window...');

  // Fullscreen transparent click-through window for subtitles
  subtitleWindow = new BrowserWindow({
    width: 800,
    height: 100,
    x: 0,
    y: 0,
    transparent: true,
    backgroundColor: '#00000000',
    frame: false,
    alwaysOnTop: true,
    resizable: false,
    show: false, // Start hidden, show after content is ready
    skipTaskbar: true,
    focusable: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: getPreloadPath('subtitle-preload.js')
    }
  });

  // Load minimal blank HTML
  const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
  html,body{margin:0;padding:0;background:transparent;}
  </style></head><body></body></html>`;
  subtitleWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);

  // Position bottom and span full width of primary display
  try {
    const { width: sw, height: sh, x: sx, y: sy } = screen.getPrimaryDisplay().workArea;
    const targetHeight = 140;
    subtitleWindow.setBounds({ x: sx, y: sy + sh - targetHeight, width: sw, height: targetHeight });
    console.log(`[SUBTITLE] Positioned subtitle window: ${sw}x${targetHeight} at (${sx}, ${sy + sh - targetHeight})`);
  } catch (error) {
    console.error('[SUBTITLE] Error positioning subtitle window:', error);
  }

  subtitleWindow.setIgnoreMouseEvents(true, { forward: true });

  subtitleWindow.on('closed', () => {
    console.log('[SUBTITLE] Subtitle window closed');
    subtitleWindow = null;
  });

  subtitleWindow.webContents.on('dom-ready', () => {
    console.log('[SUBTITLE] Subtitle window DOM ready, showing window');
    // Show window after DOM is ready
    subtitleWindow.show();
  });

  // Enable console output from subtitle window
  subtitleWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`[SUBTITLE-RENDERER] ${message}`);
  });

  console.log('[SUBTITLE] Subtitle window created successfully');

  return subtitleWindow;
}

// Register global keyboard shortcuts
function registerGlobalShortcuts() {
  // Unregister existing shortcuts first to avoid conflicts
  globalShortcut.unregisterAll();

  console.log('[SHORTCUTS] Unregistered all existing shortcuts');

  // Register global shortcuts
  const voiceTypingRegistered = globalShortcut.register('Super+Alt+V', () => {
    console.log('[SHORTCUT] Win+Alt+V (Toggle Voice Typing) triggered');
    if (mainWindow && !mainWindow.isDestroyed()) {
      console.log('[SHORTCUT] Sending toggle-voice-typing to renderer');
      mainWindow.webContents.send('global-shortcut', 'toggle-voice-typing');
    } else {
      console.log('[SHORTCUT] Main window not available for toggle-voice-typing');
    }
  });

  const liveSubtitleRegistered = globalShortcut.register('Super+Alt+L', () => {
    console.log('[SHORTCUT] Win+Alt+L (Toggle Live Subtitle) triggered');
    if (mainWindow && !mainWindow.isDestroyed()) {
      console.log('[SHORTCUT] Sending toggle-live-subtitle to renderer');
      mainWindow.webContents.send('global-shortcut', 'toggle-live-subtitle');
    } else {
      console.log('[SHORTCUT] Main window not available for toggle-live-subtitle');
    }
  });

  const hideRegistered = globalShortcut.register('Super+Alt+H', () => {
    console.log('[SHORTCUT] Win+Alt+H (Toggle Window Visibility) triggered');
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.isVisible()) {
        console.log('[SHORTCUT] Window is visible, sending hide-window');
        mainWindow.webContents.send('global-shortcut', 'hide-window');
      } else {
        console.log('[SHORTCUT] Window is hidden, sending show-window');
        mainWindow.webContents.send('global-shortcut', 'show-window');
      }
    } else {
      console.log('[SHORTCUT] Main window not available for hide/show');
    }
  });

  console.log('[SHORTCUTS] Registration results:');
  console.log('  - Win+Alt+V (Voice Typing):', voiceTypingRegistered ? 'SUCCESS' : 'FAILED');
  console.log('  - Win+Alt+L (Live Subtitle):', liveSubtitleRegistered ? 'SUCCESS' : 'FAILED');
  console.log('  - Win+Alt+H (Hide):', hideRegistered ? 'SUCCESS' : 'FAILED');

  if (!voiceTypingRegistered || !liveSubtitleRegistered || !hideRegistered) {
    console.error('[SHORTCUTS] Some shortcuts failed to register. This could be due to:');
    console.error('  - Another application using the same shortcuts');
    console.error('  - System restrictions on global shortcuts');
    console.error('  - Permission issues');
  }
}

// IPC handler for setting window size
ipcMain.handle('set-window-size', (event, size) => {
  if (!mainWindow || typeof size.width !== 'number' || typeof size.height !== 'number') return;

  const width  = Math.ceil(size.width);
  const height = Math.ceil(size.height);

  const wasResizable = mainWindow.isResizable();
  if (!wasResizable) mainWindow.setResizable(true);

  mainWindow.setContentSize(width, height);

  // Always center the window horizontally at the top
  const { width: screenWidth } = screen.getPrimaryDisplay().workAreaSize;
  const newX = Math.max(0, (screenWidth - width) / 2);
  mainWindow.setPosition(newX, 0); // Always position at top center

  if (!mainWindow.isVisible()) {
    mainWindow.show();
  }

  if (!wasResizable) mainWindow.setResizable(false);
});

// IPC handler to toggle always-on-top (helpful to show OS screen-share prompts)
ipcMain.handle('set-always-on-top', (event, flag) => {
  if (!mainWindow) return;
  try {
    mainWindow.setAlwaysOnTop(Boolean(flag));
  } catch (_) {}
});

// IPC handler for getting screen size
ipcMain.handle('get-screen-size', () => {
  const primaryDisplay = screen.getPrimaryDisplay();
  return primaryDisplay.workAreaSize;
});

// IPC handler to hide main window
ipcMain.handle('hide-window', () => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.hide();
  }
});

// IPC handler to show main window
ipcMain.handle('show-window', () => {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.show();
    mainWindow.focus();
  }
});

// IPC handler to quit the application
ipcMain.handle('quit-app', () => {
  app.quit();
});

// IPC handler for notification window
ipcMain.handle('close-notification', () => {
  if (notificationWindow && !notificationWindow.isDestroyed()) {
    notificationWindow.close();
    notificationWindow = null;
  }
  return true;
});

// IPC handler for showing notifications
ipcMain.handle('show-notification', (event, title, message) => {
  showNotification(title, message);
  return true;
});

// WebSocket connection to gateway (no authentication required)
function connectToGateway() {
  return new Promise((resolve, reject) => {
    if (ws && isConnected) {
      console.log('Already connected to gateway');
      resolve({ success: true });
      return;
    }

    console.log('[GATEWAY] Connecting to:', GATEWAY_URL);

    ws = new WebSocket(GATEWAY_URL);

    ws.on('open', () => {
      console.log('Connected to gateway');
      isConnected = true;

      // Send initial status
      sendInitialStatus();

      if (mainWindow) {
        mainWindow.webContents.send('connection-status', { connected: true });
      }

      // Setup keepalive ping/pong
      try {
        ws.isAlive = true;
        ws.on('pong', () => { ws.isAlive = true; });
        if (pingInterval) clearInterval(pingInterval);
        pingInterval = setInterval(() => {
          if (!ws || ws.readyState !== WebSocket.OPEN) return;
          if (ws.isAlive === false) {
            console.warn('Keepalive ping timeout, terminating socket');
            try { ws.terminate(); } catch (_) {}
            return;
          }
          ws.isAlive = false;
          try { ws.ping(); } catch (_) {}
        }, 15000);
      } catch (e) {
        console.warn('Failed to configure keepalive:', e?.message || e);
      }

      resolve({ success: true });
    });

    ws.on('message', (data) => {
      try {
        const message = JSON.parse(data.toString());
        handleGatewayMessage(message);
      } catch (e) {
        console.error('Error parsing gateway message:', e);
      }
    });

    ws.on('close', () => {
      console.log('Disconnected from gateway');
      isConnected = false;
      clientId = null;
      try { if (pingInterval) { clearInterval(pingInterval); pingInterval = null; } } catch (_) {}
      if (mainWindow) {
        mainWindow.webContents.send('connection-status', { connected: false });
      }
    });

    ws.on('error', (error) => {
      console.error('[GATEWAY] Connection failed:', error.message);
      console.log('[GATEWAY] Make sure the gateway service is running on', GATEWAY_URL);
      isConnected = false;
      try { if (pingInterval) { clearInterval(pingInterval); pingInterval = null; } } catch (_) {}
      if (mainWindow) {
        mainWindow.webContents.send('connection-status', { connected: false });
      }
      reject({ success: false, error: error.message });
    });

    // Set a timeout for connection attempt
    setTimeout(() => {
      if (!isConnected) {
        console.log('Connection attempt timed out');
        reject({ success: false, error: 'Connection timeout - gateway may not be running' });
      }
    }, 5000);
  });
}

function disconnectFromGateway() {
  if (ws) {
    ws.close();
    ws = null;
  }
  isConnected = false;
  clientId = null;
  try { if (pingInterval) { clearInterval(pingInterval); pingInterval = null; } } catch (_) {}
  if (mainWindow) {
    mainWindow.webContents.send('connection-status', { connected: false });
  }
}

function sendInitialStatus() {
  if (ws && isConnected && ws.readyState === WebSocket.OPEN) {
    const statusMessage = {
      type: 'get_status'
    };
    ws.send(JSON.stringify(statusMessage));
  } else {
    console.warn('[WebSocket] Cannot send initial status - WebSocket not in OPEN state');
  }
}

function handleGatewayMessage(message) {
  if (!mainWindow) return;

  switch (message.type) {
    case 'status':
      clientId = message.client_id;
      console.log('Received status:', message);
      mainWindow.webContents.send('gateway-status', message);
      break;

    case 'realtime':
      console.log('Received realtime result:', message);
      handleTranscriptionResult(message);
      mainWindow.webContents.send('realtime-result', message);
      break;

    case 'utterance_end':
      console.log('Received utterance end');
      handleUtteranceEnd();
      mainWindow.webContents.send('utterance-end', message);
      break;

    case 'error':
      console.log('Received error message:', message.message);
      // Handle authentication errors
      if (mainWindow) {
        mainWindow.webContents.send('gateway-error', message.message);
      }
      break;

    default:
      console.log('Received unknown message type:', message.type);
  }
}

// Send audio data to gateway
function sendAudioData(audioData, sampleRate = 16000) {
  if (!ws || !isConnected) {
    console.warn('Not connected to gateway, cannot send audio data');
    return;
  }

  try {
    if (ws.readyState !== WebSocket.OPEN) return;
    // Basic backpressure: drop if buffered queue is too large
    if (typeof ws.bufferedAmount === 'number' && ws.bufferedAmount > 5 * 1024 * 1024) {
      return;
    }
    // Create metadata
    const metadata = JSON.stringify({ sampleRate: sampleRate });
    const metadataLength = Buffer.alloc(4);
    metadataLength.writeUInt32LE(Buffer.byteLength(metadata), 0);

    // Combine metadata length, metadata, and audio data
    const message = Buffer.concat([
      metadataLength,
      Buffer.from(metadata),
      Buffer.from(audioData)
    ]);

    ws.send(message);
  } catch (error) {
    console.error('Error sending audio data:', error);
  }
}

// Store current language settings
let currentSourceLang = 'en';
let currentTargetLang = 'vi';

// Update languages
function updateLanguages(sourceLang, targetLang) {
  // Store the current language settings
  currentSourceLang = sourceLang;
  currentTargetLang = targetLang;
  
  if (ws && isConnected && ws.readyState === WebSocket.OPEN) {
    const message = {
      type: 'set_langs',
      source_language: sourceLang,
      target_language: targetLang
    };
    ws.send(JSON.stringify(message));
    console.log('Updated languages:', sourceLang, '->', targetLang);
  } else {
    console.warn('[WebSocket] Cannot update languages - WebSocket not in OPEN state');
  }
}

// Send start over command
function sendStartOver() {
  if (ws && isConnected && ws.readyState === WebSocket.OPEN) {
    const message = {
      type: 'start_over'
    };
    ws.send(JSON.stringify(message));
    console.log('Sent start over command');
  } else {
    console.warn('[WebSocket] Cannot send start over - WebSocket not in OPEN state');
  }
}

// IPC handlers for client functionality
ipcMain.handle('connect-gateway', async () => {
  console.log('[IPC] connect-gateway called');
  try {
    const result = await connectToGateway();
    return result;
  } catch (error) {
    console.log('[IPC] Gateway connection failed:', error);
    return error;
  }
});

ipcMain.handle('disconnect-gateway', () => {
  disconnectFromGateway();
  return { success: true };
});

ipcMain.handle('send-audio-data', (event, audioData, sampleRate) => {
  sendAudioData(audioData, sampleRate);
  return { success: true };
});

// Fast, fire-and-forget audio streaming channel
ipcMain.on('audio-chunk', (event, audioData, sampleRate) => {
  try { sendAudioData(audioData, sampleRate); } catch (_) {}
});

ipcMain.handle('update-languages', (event, sourceLang, targetLang) => {
  updateLanguages(sourceLang, targetLang);
  return { success: true };
});

ipcMain.handle('send-start-over', () => {
  sendStartOver();
  return { success: true };
});

ipcMain.handle('get-connection-status', () => {
  return { connected: isConnected, clientId };
});

// Live transcription and typing simulation
let liveTranscriptionManager = null;
let typingSimulationManager = null;

// Initialize live transcription
function initLiveTranscription() {
  try {
    console.log('[INIT] Initializing live transcription manager');
    // Always create the live transcription manager for Electron
    liveTranscriptionManager = {
        active: false,
        currentText: '',
        start: function() {
          this.active = true;
          console.log('Live transcription started');
          try { if (mainWindow) mainWindow.webContents.send('live-transcription-update', { text: '' }); } catch (_) {}
          // Create subtitle window directly instead of calling renderer API
          try { createSubtitleWindow(); } catch (error) {
            console.error('Error creating subtitle window:', error);
          }
        },
        stop: function() {
          this.active = false;
          console.log('Live transcription stopped');
          // Hide subtitle window directly instead of calling renderer API
          try {
            if (subtitleWindow && !subtitleWindow.isDestroyed()) {
              subtitleWindow.hide();
            }
          } catch (error) {
            console.error('Error hiding subtitle window:', error);
          }
        },
        updateText: function(text) {
          console.log(`[SUBTITLE] updateText called with: "${text}"`);
          this.currentText = text;
          if (mainWindow) {
            mainWindow.webContents.send('live-transcription-update', { text });
          }
          // Send IPC directly to subtitle window instead of executing JavaScript
          if (!subtitleWindow || subtitleWindow.isDestroyed()) {
            console.log('[SUBTITLE] Creating subtitle window for text update');
            createSubtitleWindow();
          }
          if (subtitleWindow && !subtitleWindow.isDestroyed()) {
            const safeText = String(text ?? '');
            console.log(`[SUBTITLE] Sending subtitle-update: "${safeText}"`);
            subtitleWindow.webContents.send('subtitle-update', safeText);
          } else {
            console.error('[SUBTITLE] Subtitle window not available for text update');
          }
        },
        updateDualText: function(transcription, translation) {
          console.log(`[SUBTITLE] updateDualText called with transcription: "${transcription}", translation: "${translation}"`);
          this.currentText = translation || transcription;
          if (mainWindow) {
            mainWindow.webContents.send('live-transcription-update', {
              text: translation || transcription,
              transcription: transcription,
              translation: translation
            });
          }
          // Send IPC directly to subtitle window instead of executing JavaScript
          if (!subtitleWindow || subtitleWindow.isDestroyed()) {
            console.log('[SUBTITLE] Creating subtitle window for dual text update');
            createSubtitleWindow();
          }
          if (subtitleWindow && !subtitleWindow.isDestroyed()) {
            const data = {
              transcription: String(transcription ?? ''),
              translation: String(translation ?? '')
            };
            console.log(`[SUBTITLE] Sending subtitle-update-dual:`, data);
            subtitleWindow.webContents.send('subtitle-update-dual', data);
          } else {
            console.error('[SUBTITLE] Subtitle window not available for dual text update');
          }
        }
      };
    console.log('[INIT] Live transcription manager initialized successfully');
  } catch (error) {
    console.error('[INIT] Error initializing live transcription:', error);
  }
}

// Initialize typing simulation
function initTypingSimulation() {
  // ===== Internal state =====
  let currentDisplayedText = ""; // what we've currently pasted in this utterance
  let previousUtteranceText = ""; // what the previous utterance was
  let isFirstTextOfUtterance = true; // true if we haven't pasted anything yet in this utterance
  // Carry-over formatting for a whole utterance so all incremental updates include the same prefix/case
  let utterancePrefix = "";           // e.g. " " when appending after previous utterance
  let shouldUncapitalize = false;      // whether to uncapitalize the first word of all updates in this utterance
  let lastOperationTime = 0; // timestamp of last paste operation
  let isProcessingOperation = false; // flag to prevent overlapping operations
  let operationQueue = []; // queue for serializing operations
  const MIN_OPERATION_SPACING = 0; // no spacing between operations for maximum speed

  // ===== Utility functions =====
  const preprocessText = (text) => {
    if (!text) return "";
    let t = text;
    t = t.replace(/\.\.\./g, "");
    t = t.replace(/[\t\n\r]+/g, " ");
    t = t.replace(/\s+([,!?;:])/g, '$1');
    t = t.replace(/\s+(\.)/g, '$1');
    t = t.replace(/([,!?;:])\s*(\w)/g, '$1 $2');
    t = t.replace(/(?<!\d)\.\s*(\w)/g, '. $1');
    t = t.replace(/\s{2,}/g, " ");
    return t.trim();
  };

  // Function to uncapitalize the first word of a string
  const uncapitalizeFirstWord = (text) => {
    if (!text) return text;

    // Don't uncapitalize if it starts with a non-letter (number, punctuation, etc.)
    if (!/^[A-Z]/i.test(text)) return text;
    
    // Don't uncapitalize proper nouns like "I", "John", etc.
    const properNouns = ["I", "I'm", "I'll", "I've", "I'd"];
    const firstWord = text.split(/\s+/)[0];
    if (properNouns.includes(firstWord)) return text;
    
    // Uncapitalize the first character
    return text.charAt(0).toLowerCase() + text.slice(1);
  };

  // Execute operations in sequence with proper timing
  const executeOperation = (operation) => {
    if (isProcessingOperation) {
      // Queue the operation if another is in progress
      operationQueue.push(operation);
      return;
    }

    isProcessingOperation = true;
    
    // Ensure minimum spacing between operations
    const now = Date.now();
    const timeSinceLastOp = now - lastOperationTime;
    const delay = timeSinceLastOp < MIN_OPERATION_SPACING ? 
                  MIN_OPERATION_SPACING - timeSinceLastOp : 0;
    
    setTimeout(() => {
      try {
        operation();
      } catch (e) {
        console.error("[TYPING] Operation failed:", e);
      }
      
      lastOperationTime = Date.now();
      isProcessingOperation = false;
      
      // Process next operation in queue if any
      if (operationQueue.length > 0) {
        const nextOperation = operationQueue.shift();
        executeOperation(nextOperation);
      }
    }, delay);
  };

  const pasteText = (text) => {
    if (!text) return;
    
    // Calculate what the text would be after formatting (to compare with currentDisplayedText)
    let textCore = text;
    let textToPaste = "";
    
    if (isFirstTextOfUtterance) {
      // For first text, apply prefix and uncapitalize if needed
      let prefix = "";
      let shouldUncap = false;
      
      if (previousUtteranceText) {
        const prevText = previousUtteranceText.trim();
        const endsWithSentenceEnd = prevText.endsWith('.') || 
                                   prevText.endsWith('!') || 
                                   prevText.endsWith('?');
        prefix = ' ';
        shouldUncap = !endsWithSentenceEnd;
        if (shouldUncap) {
          textCore = uncapitalizeFirstWord(textCore);
        }
      }
      textToPaste = prefix + textCore;
    } else {
      // For subsequent text, use the utterance's formatting
      textCore = shouldUncapitalize ? uncapitalizeFirstWord(text) : text;
      textToPaste = utterancePrefix + textCore;
    }
    
    // Skip if the formatted text is identical to what's already displayed (trim both for comparison)
    if (textToPaste.trim() === currentDisplayedText.trim()) {
      console.log('[TYPING] Skipping paste - text unchanged after formatting');
      return;
    }

    executeOperation(() => {
      try {
        if (isFirstTextOfUtterance) {
          // First text of utterance: decide prefix/case and remember for the whole utterance
          let textCore = text;
          utterancePrefix = "";
          shouldUncapitalize = false;

          if (previousUtteranceText) {
            // Check if previous text ended with sentence-ending punctuation
            // Trim to handle any edge cases with whitespace
            const prevText = previousUtteranceText.trim();
            const endsWithSentenceEnd = prevText.endsWith('.') || 
                                       prevText.endsWith('!') || 
                                       prevText.endsWith('?');

            utterancePrefix = ' ';
            shouldUncapitalize = !endsWithSentenceEnd;
            if (shouldUncapitalize) {
              textCore = uncapitalizeFirstWord(textCore);
              console.log('[TYPING] Uncapitalizing - prev ended with:', prevText.slice(-20));
            } else {
              console.log('[TYPING] Keeping capitalization - prev ended with:', prevText.slice(-20));
            }

            console.log('[TYPING] First text of new utterance, appending to previous');
            // Press End key to move cursor to end
            robot.keyTap('end');
          }

          const textToPaste = utterancePrefix + textCore;
          clipboard.writeText(textToPaste);
          robot.keyTap('v', ['control']);

          currentDisplayedText = textToPaste;
          isFirstTextOfUtterance = false;
          console.log('[TYPING] First text pasted');
        } else {
          // Subsequent text within same utterance: undo and paste
          robot.keyTap('z', ['control']);

          // Immediate paste after undo (no delay needed on modern systems)
          // Preserve formatting from the first chunk of the utterance
          // MUST include utterancePrefix to maintain spacing between utterances
          const textCore = shouldUncapitalize ? uncapitalizeFirstWord(text) : text;
          const textToPaste = utterancePrefix + textCore;  // Keep utterancePrefix for all pastes in utterance
          clipboard.writeText(textToPaste);
          robot.keyTap('v', ['control']);
          currentDisplayedText = textToPaste;
          console.log('[TYPING] Subsequent text pasted (after undo)');
        }
    } catch (e) {
      console.error("[TYPING] Error during paste:", e);
    }
    });
  };

  const handleFinalText = (text) => {
    if (!text) return;

    // First, clear any pending operations to avoid duplicates
    operationQueue = [];
    
    // Calculate what the final text will be BEFORE async operations
    // This prevents race conditions with the next utterance
    let finalTextToPaste = "";
    
    if (isFirstTextOfUtterance) {
      // First text of utterance as final: decide prefix/case and remember
      let textCore = text;
      utterancePrefix = "";
      shouldUncapitalize = false;

      if (previousUtteranceText) {
        // Trim to handle any edge cases with whitespace
        const prevText = previousUtteranceText.trim();
        const endsWithSentenceEnd = prevText.endsWith('.') || 
                                   prevText.endsWith('!') || 
                                   prevText.endsWith('?');
        utterancePrefix = ' ';
        shouldUncapitalize = !endsWithSentenceEnd;
        if (shouldUncapitalize) {
          textCore = uncapitalizeFirstWord(textCore);
          console.log('[TYPING] Final text: Uncapitalizing - prev ended with:', prevText.slice(-20));
        } else {
          console.log('[TYPING] Final text: Keeping capitalization - prev ended with:', prevText.slice(-20));
        }
      }

      finalTextToPaste = utterancePrefix + textCore;
    } else {
      // Not first text: calculate what will be pasted
      const textCore = shouldUncapitalize ? uncapitalizeFirstWord(text) : text;
      finalTextToPaste = utterancePrefix + textCore;
    }
    
    // Store IMMEDIATELY to prevent race conditions with next utterance
    previousUtteranceText = finalTextToPaste;
    console.log('[TYPING] Stored previous utterance text:', finalTextToPaste.substring(0, 30));
    
    // Now perform the actual paste operations
    executeOperation(() => {
      try {
        if (isFirstTextOfUtterance) {
          if (previousUtteranceText.startsWith(' ')) {
            // If there was a previous utterance, move to end first
            robot.keyTap('end');
          }

          clipboard.writeText(finalTextToPaste);
          robot.keyTap('v', ['control']);
          console.log('[TYPING] Final text (first of utterance) appended');
        } else {
          // Not first text: undo and paste
          robot.keyTap('z', ['control']);

          // Immediate paste after undo (no delay needed)
          clipboard.writeText(finalTextToPaste);
          robot.keyTap('v', ['control']);
          console.log('[TYPING] Final text pasted (after undo)');
        }

        // Add a single commit operation to finalize this utterance
        executeOperation(() => {
          console.log('[TYPING] Finalizing utterance - pressing End key');
          // Press End key to move cursor to end of text
          robot.keyTap('end');
          
          // Reset for next utterance
          currentDisplayedText = "";
          isFirstTextOfUtterance = true;
          utterancePrefix = "";
          shouldUncapitalize = false;
          console.log('[TYPING] Utterance finalized, ready for next utterance');
        });
      } catch (e) {
        console.error("[TYPING] Error during final paste:", e);
      }
    });
  };

  // ===== Public API =====
  typingSimulationManager = {
    active: false,
    lastReceivedText: "", // Store the last text we received for use with utterance_end
    
    start: function() {
      if (this.active) return;
      this.active = true;
      // Reset state for a new session
      currentDisplayedText = "";
      previousUtteranceText = "";
      isFirstTextOfUtterance = true;
      isProcessingOperation = false;
      operationQueue = [];
      lastOperationTime = 0;
      this.lastReceivedText = "";
      console.log('[TYPING] Typing simulation started');
    },
    
    stop: function() {
      this.active = false;
      // Clear any pending operations
      operationQueue = [];
      isProcessingOperation = false;
      console.log('[TYPING] Typing simulation stopped');
    },
    
    handleText: function(text, isFinal) {
      if (!this.active || !text) return;

      const processedText = preprocessText(text);
      if (!processedText) return;

      // Store the processed text as our last received text
      this.lastReceivedText = processedText;
      
      if (isFinal) {
        handleFinalText(processedText);
        } else {
        pasteText(processedText);
      }
    },
    
    // Call this method when utterance_end is received to commit current text
    commitCurrentUtterance: function() {
      if (!this.active) return;
      
      // Important: There should be no operations in the queue at this point
      // as we've cleared it in the handleUtteranceEnd function
      
      // Add a single operation to finalize the utterance
      executeOperation(() => {
        console.log('[TYPING] Committing utterance (utterance_end received)');
        
        try {
          // Move cursor to end of text
          robot.keyTap('end');
          
          // Store current displayed text if needed
          if (currentDisplayedText && !previousUtteranceText) {
            previousUtteranceText = currentDisplayedText;
          }
          
          // Reset for next utterance
        currentDisplayedText = "";
          isFirstTextOfUtterance = true;
          
          console.log('[TYPING] Utterance committed successfully');
        } catch (e) {
          console.error('[TYPING] Error committing utterance:', e);
        }
      });
      
      // Reset the last received text
      this.lastReceivedText = "";
    }
  };
  console.log('[TYPING] Typing simulation module initialized');
}

// Handle transcription results based on current mode
function handleTranscriptionResult(result) {
  const transcriptionText = result.text || '';
  const translationText = result.translation || '';
  const isFinal = result.is_final || result.isFinal || false; // Check for is_final flag
  const segmentId = result.segment_id || ''; // Segment ID for logging

  // Log the type of result for debugging
  console.log(`[RECEIVED] ${isFinal ? 'Final' : 'Non-final'} result for segment ${segmentId}`);

  if (currentMode === 'subtitle' && liveTranscriptionManager) {
    // Determine if translation is enabled based on language settings
    const translationEnabled = currentSourceLang !== currentTargetLang;

    if (translationEnabled) {
      // Always drive dual overlay when translation is enabled
      liveTranscriptionManager.updateDualText(transcriptionText, translationText);
    } else {
      // Translation disabled: show single subtitle (transcription at bottom)
      const displayText = transcriptionText;
      liveTranscriptionManager.updateText(displayText);
    }
  } else if (currentMode === 'typing' && typingSimulationManager) {
    // For typing mode, check if translation is enabled
    const translationEnabled = currentSourceLang !== currentTargetLang;

    // Determine which text to use (gateway ensures we only receive the correct text)
    const textToHandle = translationEnabled ? translationText : transcriptionText;

    if (textToHandle) {
      // Only process if we actually have text
      typingSimulationManager.handleText(textToHandle, isFinal);
      
      // Don't log the entire text, just a preview to reduce log spam
      const textPreview = textToHandle.length > 30 ? 
        textToHandle.substring(0, 27) + '...' : 
        textToHandle;
      console.log(`[TYPING] ${isFinal ? 'Final' : 'Non-final'} text handled:`, textPreview);
    }
  }
}

// Handle utterance end
function handleUtteranceEnd() {
  console.log('[TYPING] Utterance end received');
  
  // Immediately clear any pending operations
  // This prevents duplicate pastes when utterance_end is received
  if (typeof operationQueue !== 'undefined') {
    operationQueue = [];
    console.log('[TYPING] Cleared operation queue to prevent duplicates');
  }
  
  // Now commit the utterance
    if (currentMode === 'typing' && typingSimulationManager) {
    typingSimulationManager.commitCurrentUtterance();
  }
}

// IPC handlers for mode switching
ipcMain.handle('set-mode', (event, mode) => {
  if (mode === 'typing') {
    if (liveTranscriptionManager) liveTranscriptionManager.stop();
    if (typingSimulationManager) typingSimulationManager.start();
    currentMode = 'typing';
    console.log('Switched to mode:', mode);
    return { success: true };
  } else if (mode === 'subtitle') {
    // Check if WebSocket is connected before starting subtitle mode
    if (!isConnected) {
      console.log('Cannot start live subtitle: WebSocket not connected');
      return { success: false, error: 'Not connected to gateway. Please wait for connection.' };
    }

    if (typingSimulationManager) typingSimulationManager.stop();
    if (liveTranscriptionManager) liveTranscriptionManager.start();
    currentMode = 'subtitle';
    console.log('Switched to mode:', mode);
    return { success: true };
  }

  return { success: false, error: 'Unknown mode' };
});

ipcMain.handle('get-mode', () => {
  return currentMode;
});


// This method will be called when Electron has finished initialization
app.whenReady().then(async () => {
  // Initialize transcription modules
  initLiveTranscription();
  initTypingSimulation();

  // Initialize with default language settings
  console.log('Initializing with default languages:', currentSourceLang, '->', currentTargetLang);

  // Proactively allow media and display-capture permissions
  const ses = session.defaultSession;
  ses.setPermissionRequestHandler((wc, permission, callback) => {
    if (permission === 'media' || permission === 'display-capture') {
      return callback(true);
    }
    callback(false);
  });

  // Auto-approve display media with system audio loopback on Windows
  if (typeof ses.setDisplayMediaRequestHandler === 'function') {
    ses.setDisplayMediaRequestHandler((request, callback) => {
      // Choose first screen and request loopback audio
      const { desktopCapturer } = require('electron');
      desktopCapturer.getSources({ types: ['screen'] }).then((sources) => {
        const primary = sources[0];
        if (!primary) {
          callback({ video: null, audio: 'none' });
          return;
        }
        callback({
          video: primary,
          audio: 'loopback'
        });
      }).catch(() => {
        callback({ video: null, audio: 'none' });
      });
    });
  }

  // Register custom protocol to serve static files
  protocol.interceptFileProtocol('file', (request, callback) => {
    const url = request.url.substr(7);    // all urls start with 'file://'
    const outPath = path.join(__dirname, '..', 'out');

    // If the URL contains _next, serve from out directory
    if (url.includes('/_next/')) {
      const filePath = path.join(outPath, url.replace(/^.*\/_next\//, '_next/'));
      callback({ path: filePath });
    } else {
      // Default file serving
      callback({ path: path.normalize(url) });
    }
  });

  // Create main window directly (no authentication required)
  console.log('Creating main window for open-source version');
  createWindow();
  registerGlobalShortcuts();

  // Explicitly show the window after creation
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.show();
    console.log('Main window shown');
  }
});

// Cleanup global shortcuts before quitting
app.on('before-quit', () => {
  console.log('Unregistering global shortcuts before quit');
  globalShortcut.unregisterAll();
});

// Quit when all windows are closed
app.on('window-all-closed', () => {
  console.log('[APP] All windows closed, quitting app');
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
    registerGlobalShortcuts();
  }
});

// Prevent new window creation
app.on('web-contents-created', (_, contents) => {
  contents.on('new-window', (event) => {
    event.preventDefault();
  });
});

// IPC from renderer to show/hide/update subtitles
ipcMain.handle('subtitle-show', () => {
  createSubtitleWindow();
  return true;
});
ipcMain.handle('subtitle-hide', () => {
  if (subtitleWindow && !subtitleWindow.isDestroyed()) subtitleWindow.hide();
  return true;
});
ipcMain.on('subtitle-text', (_e, text) => {
  console.log('[IPC] subtitle-text received:', text);
  if (!subtitleWindow || subtitleWindow.isDestroyed()) {
    console.log('[IPC] Creating subtitle window for subtitle-text');
    createSubtitleWindow();
  }
  if (subtitleWindow && !subtitleWindow.isDestroyed()) {
    subtitleWindow.webContents.send('subtitle-update', String(text ?? ''));
  }
});
ipcMain.on('subtitle-text-dual', (_e, data) => {
  console.log('[IPC] subtitle-text-dual received:', data);
  if (!subtitleWindow || subtitleWindow.isDestroyed()) {
    console.log('[IPC] Creating subtitle window for subtitle-text-dual');
    createSubtitleWindow();
  }
  if (subtitleWindow && !subtitleWindow.isDestroyed()) {
    subtitleWindow.webContents.send('subtitle-update-dual', {
      transcription: String(data?.transcription ?? ''),
      translation: String(data?.translation ?? '')
    });
  }
});

// No longer needed - using fixed height with CSS animations
// ipcMain.on('set-height', (_event, height) => {
//   if (!mainWindow) return;
//   if (typeof height !== 'number' || !Number.isFinite(height)) return;
//   const clamped = Math.max(200, Math.min(Math.ceil(height), 800));
//   mainWindow.setContentSize(1200, clamped, true);
// });
