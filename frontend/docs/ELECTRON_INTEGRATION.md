# Electron Integration Guide

Comprehensive guide to Electron architecture, main/renderer process communication, and desktop integration in the Nova Voice application.

## 🏗️ Electron Architecture Overview

Electron enables web technologies to run as desktop applications. Nova Voice uses a split-process architecture with secure inter-process communication.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Renderer      │────│   Main Process  │────│   System APIs   │
│   Process       │    │                 │    │                 │
│ • React UI      │    │ • Window Mgmt   │    │ • File System   │
│ • Web APIs      │    │ • WebSocket     │    │ • Clipboard     │
│ • No Node.js    │    │ • IPC Bridge    │    │ • Keyboard      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │
        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐
│   Preload       │    │   Backend       │
│   Scripts       │    │   Services      │
│                 │    │                 │
│ • Secure IPC    │    │ • Gateway       │
│ • API Exposure  │    │ • STT Worker    │
│ • Context Bridge │    │ • Translation   │
└─────────────────┘    └─────────────────┘
```

## 🎯 Core Concepts

### Main vs Renderer Processes

#### Main Process (`electron/main.js`)
- **Node.js Environment**: Full access to Node.js APIs and system resources
- **Application Lifecycle**: Controls app startup, windows, and shutdown
- **System Integration**: File system, clipboard, keyboard simulation
- **Security**: Can access all system resources (use carefully)

#### Renderer Process (React App)
- **Browser Environment**: Limited to web APIs only
- **UI Rendering**: React components and DOM manipulation
- **User Interaction**: Event handling and UI updates
- **Security**: Sandboxed, no direct system access

### Context Isolation & Security

Electron implements multiple security layers:

```javascript
// Main process - secure configuration
const mainWindow = new BrowserWindow({
  webPreferences: {
    nodeIntegration: false,      // No Node.js in renderer
    contextIsolation: true,      // Separate contexts
    enableRemoteModule: false,   // No remote module
    preload: 'preload.js'        // Secure API bridge
  }
})
```

## 🔧 Main Process Architecture

### Window Management

The main process creates and manages multiple window types:

#### Main Application Window
```javascript
const mainWindow = new BrowserWindow({
  width: 1050,
  height: 600,
  frame: false,              // Frameless for custom UI
  transparent: true,         // Glassmorphism effect
  alwaysOnTop: false,        // User configurable
  webPreferences: {
    preload: path.join(__dirname, 'preload.js')
  }
})
```

#### Subtitle Overlay Window
```javascript
const subtitleWindow = new BrowserWindow({
  width: screenWidth,
  height: 140,
  frame: false,
  transparent: true,
  alwaysOnTop: true,
  skipTaskbar: true,         // Hidden from taskbar
  focusable: false,          // Click-through enabled
  // Positioned at screen bottom
})
```

#### Notification Windows
```javascript
const notificationWindow = new BrowserWindow({
  width: 300,
  height: 80,
  frame: false,
  transparent: true,
  alwaysOnTop: true,
  show: false,               // Initially hidden
  // Auto-hide after timeout
})
```

### WebSocket Client Integration

The main process maintains the WebSocket connection to the backend:

```javascript
class WebSocketManager {
  constructor() {
    this.ws = null
    this.reconnectAttempts = 0
  }

  connect(url) {
    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      this.reconnectAttempts = 0
      this.sendToRenderer('gateway-connected', {})
    }

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      this.handleMessage(data)
    }

    this.ws.onclose = () => {
      this.scheduleReconnect()
    }

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  handleMessage(data) {
    // Forward to renderer process
    mainWindow.webContents.send('websocket-message', data)
  }

  sendAudio(audioData, sampleRate) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      // Send binary audio data
      const metadata = { sampleRate }
      const message = createBinaryMessage(metadata, audioData)
      this.ws.send(message)
    }
  }
}
```

### IPC Communication Bridge

Secure communication between main and renderer processes:

```javascript
// Main process - expose APIs
ipcMain.handle('connect-gateway', async () => {
  try {
    await websocketManager.connect(config.gatewayUrl)
    return { success: true }
  } catch (error) {
    return { success: false, error: error.message }
  }
})

ipcMain.handle('send-audio-data', async (event, audioData, sampleRate) => {
  websocketManager.sendAudio(audioData, sampleRate)
  return { success: true }
})

ipcMain.handle('set-mode', async (event, mode) => {
  websocketManager.sendMessage({ type: 'set_mode', mode })
  return { success: true }
})
```

## 🛡️ Preload Scripts

Preload scripts provide a secure bridge between processes:

### Main Preload Script (`preload.js`)

```javascript
const { contextBridge, ipcRenderer } = require('electron')

// Expose protected methods to renderer
contextBridge.exposeInMainWorld('electronAPI', {
  // Gateway operations
  connectGateway: () => ipcRenderer.invoke('connect-gateway'),
  disconnectGateway: () => ipcRenderer.invoke('disconnect-gateway'),
  sendAudioData: (audioData, sampleRate) => ipcRenderer.invoke('send-audio-data', audioData, sampleRate),
  setMode: (mode) => ipcRenderer.invoke('set-mode', mode),
  updateLanguages: (source, target) => ipcRenderer.invoke('update-languages', source, target),
  sendStartOver: () => ipcRenderer.invoke('send-start-over'),

  // Window management
  hideWindow: () => ipcRenderer.invoke('hide-window'),
  quitApp: () => ipcRenderer.invoke('quit-app'),
  setWindowSize: (size) => ipcRenderer.invoke('set-window-size', size),

  // Events
  onConnectionStatus: (callback) => ipcRenderer.on('connection-status', callback),
  onTranscriptionResult: (callback) => ipcRenderer.on('transcription-result', callback),
  onUtteranceEnd: (callback) => ipcRenderer.on('utterance-end', callback),

  // Shortcuts
  onShortcut: (callback) => ipcRenderer.on('shortcut-triggered', callback)
})
```

### Specialized Preload Scripts

#### Subtitle Preload (`subtitle-preload.js`)
```javascript
// Secure API for subtitle window
contextBridge.exposeInMainWorld('subtitleAPI', {
  updateText: (transcription, translation) => {
    ipcRenderer.invoke('update-subtitle-text', { transcription, translation })
  },

  onTextUpdate: (callback) => {
    ipcRenderer.on('subtitle-text-update', callback)
  }
})
```

## 🎛️ System Integration

### Voice Typing Simulation

Uses robotjs for native system automation:

```javascript
const robot = require('robotjs')

class TypingSimulator {
  async pasteText(text) {
    // Copy to clipboard
    clipboard.writeText(text)

    // Small delay for clipboard to settle
    await new Promise(resolve => setTimeout(resolve, 10))

    // Simulate paste
    robot.keyTap('v', 'control')
  }

  async undoLastPaste() {
    robot.keyTap('z', 'control')

    // Wait for undo to complete
    await new Promise(resolve => setTimeout(resolve, 50))
  }

  async replaceText(oldText, newText) {
    await this.undoLastPaste()
    await this.pasteText(newText)
  }
}
```

### Global Shortcuts

Register system-wide keyboard shortcuts:

```javascript
const { globalShortcut } = require('electron')

class ShortcutManager {
  constructor(mainWindow) {
    this.mainWindow = mainWindow
    this.shortcuts = new Map()
  }

  register(shortcut, action) {
    if (globalShortcut.isRegistered(shortcut)) {
      globalShortcut.unregister(shortcut)
    }

    const success = globalShortcut.register(shortcut, () => {
      // Send to renderer process
      this.mainWindow.webContents.send('shortcut-triggered', action)
    })

    if (success) {
      this.shortcuts.set(shortcut, action)
    }

    return success
  }

  unregister(shortcut) {
    globalShortcut.unregister(shortcut)
    this.shortcuts.delete(shortcut)
  }

  unregisterAll() {
    globalShortcut.unregisterAll()
    this.shortcuts.clear()
  }
}

// Usage
shortcutManager.register('Win+Alt+V', 'toggle-voice-typing')
shortcutManager.register('Win+Alt+L', 'toggle-live-subtitles')
shortcutManager.register('Win+Alt+H', 'hide-window')
```

### Dynamic Window Sizing

Handles window resizing based on UI state:

```javascript
class WindowManager {
  setWindowSize(mainWindow, width, height, animate = true) {
    const [currentWidth, currentHeight] = mainWindow.getSize()

    if (animate && Math.abs(height - currentHeight) > 10) {
      // Smooth animation for larger changes
      this.animateResize(mainWindow, width, height)
    } else {
      // Instant resize for small changes
      mainWindow.setSize(width, height)
    }
  }

  animateResize(mainWindow, targetWidth, targetHeight) {
    const [startWidth, startHeight] = mainWindow.getSize()
    const duration = 300 // ms
    const steps = 10
    const stepDuration = duration / steps

    for (let i = 1; i <= steps; i++) {
      setTimeout(() => {
        const progress = i / steps
        const width = Math.round(startWidth + (targetWidth - startWidth) * progress)
        const height = Math.round(startHeight + (targetHeight - startHeight) * progress)
        mainWindow.setSize(width, height)
      }, stepDuration * i)
    }
  }
}
```

## 🔒 Security Architecture

### Process Isolation

1. **Renderer Sandboxing**: No direct Node.js access
2. **Context Isolation**: Separate JavaScript contexts
3. **Preload Scripts**: Carefully controlled API exposure
4. **Permission Model**: Granular capability grants

### Secure API Design

```javascript
// Only expose necessary APIs
contextBridge.exposeInMainWorld('electronAPI', {
  // Safe operations only
  connectGateway: () => ipcRenderer.invoke('connect-gateway'),
  sendAudioData: (data, rate) => {
    // Validate input types and sizes
    if (!isValidAudioData(data)) return
    return ipcRenderer.invoke('send-audio-data', data, rate)
  }
})
```

### Input Validation

```javascript
// Validate all IPC inputs
ipcMain.handle('send-audio-data', async (event, audioData, sampleRate) => {
  // Type checking
  if (!ArrayBuffer.isView(audioData) || typeof sampleRate !== 'number') {
    throw new Error('Invalid audio data format')
  }

  // Size limits
  if (audioData.length > MAX_AUDIO_SIZE) {
    throw new Error('Audio data too large')
  }

  // Rate validation
  if (sampleRate < 8000 || sampleRate > 48000) {
    throw new Error('Invalid sample rate')
  }

  // Process audio
  return await websocketManager.sendAudio(audioData, sampleRate)
})
```

## 🚀 Development and Debugging

### Development Mode Features

```javascript
// Enable dev tools in development
if (process.env.NODE_ENV === 'development') {
  mainWindow.webContents.openDevTools()

  // Hot reload for main process
  require('electron-reloader')(module)

  // Additional logging
  console.log('Development mode enabled')
}
```

### Debugging IPC Communication

```javascript
// Log all IPC messages (development only)
if (process.env.NODE_ENV === 'development') {
  ipcMain.on('any', (event, command, ...args) => {
    console.log(`IPC: ${command}`, args)
  })

  ipcRenderer.on('any', (event, channel, ...args) => {
    console.log(`IPC Received: ${channel}`, args)
  })
}
```

### Testing Electron Features

```javascript
// Unit test IPC handlers
const { ipcMain } = require('electron')

describe('IPC Handlers', () => {
  test('connect-gateway returns success', async () => {
    const result = await ipcMain.emit('connect-gateway')
    expect(result.success).toBe(true)
  })
})
```

## 📦 Build and Packaging

### Electron Builder Configuration

```json
// electron-builder.json
{
  "appId": "com.nova.voice",
  "productName": "Nova Voice",
  "directories": {
    "output": "dist"
  },
  "files": [
    "out/**/*",
    "electron/**/*",
    "node_modules/**/*",
    "package.json"
  ],
  "mac": {
    "target": "dmg"
  },
  "win": {
    "target": "nsis"
  },
  "linux": {
    "target": "AppImage"
  }
}
```

### Build Scripts

```json
// package.json
{
  "scripts": {
    "build": "next build",
    "electron": "electron electron/main.js",
    "electron-build": "electron-builder",
    "dist": "npm run build && npm run electron-build"
  }
}
```

## 🐛 Troubleshooting

### Common Issues

#### Window Not Showing
```javascript
// Check window creation
console.log('Window created:', mainWindow.id)
console.log('Window visible:', mainWindow.isVisible())

// Force show window
mainWindow.show()
mainWindow.focus()
```

#### IPC Not Working
```javascript
// Check preload script loading
console.log('Preload script loaded')

// Test IPC manually
ipcRenderer.invoke('test-connection')
  .then(result => console.log('IPC works:', result))
  .catch(error => console.error('IPC failed:', error))
```

#### WebSocket Connection Issues
```javascript
// Check WebSocket state
console.log('WebSocket readyState:', ws.readyState)

// Test connection manually
const testWs = new WebSocket('ws://localhost:5026')
testWs.onopen = () => console.log('WebSocket connection successful')
testWs.onerror = (error) => console.error('WebSocket connection failed:', error)
```

#### Permission Issues
```javascript
// Check microphone permissions
navigator.permissions.query({ name: 'microphone' })
  .then(result => console.log('Microphone permission:', result.state))

// Request permissions explicitly
navigator.mediaDevices.getUserMedia({ audio: true })
  .then(() => console.log('Microphone access granted'))
  .catch(error => console.error('Microphone access denied:', error))
```

## 📊 Performance Optimization

### Memory Management
```javascript
// Clean up event listeners
mainWindow.on('closed', () => {
  // Remove all listeners
  ipcMain.removeAllListeners()

  // Close WebSocket
  if (websocketManager.ws) {
    websocketManager.ws.close()
  }

  // Clear timers and intervals
  clearInterval(healthCheckInterval)
})
```

### Resource Monitoring
```javascript
// Monitor main process memory
setInterval(() => {
  const memUsage = process.memoryUsage()
  console.log(`Memory: ${Math.round(memUsage.heapUsed / 1024 / 1024)}MB`)
}, 30000)
```

## 🔄 Update Mechanism

### Auto-Updates (Future)
```javascript
const { autoUpdater } = require('electron-updater')

autoUpdater.checkForUpdatesAndNotify()

autoUpdater.on('update-available', () => {
  mainWindow.webContents.send('update-available')
})

autoUpdater.on('update-downloaded', () => {
  autoUpdater.quitAndInstall()
})
```

## 📚 Related Documentation

- **[DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md)** - Development workflow
- **[COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md)** - React component patterns
- **[WEBSOCKET_CLIENT.md](WEBSOCKET_CLIENT.md)** - WebSocket communication
- **[BUILD_DEPLOYMENT.md](BUILD_DEPLOYMENT.md)** - Packaging and distribution

---

**Electron integration provides the bridge between web technologies and native desktop capabilities, enabling secure and performant desktop applications.**
