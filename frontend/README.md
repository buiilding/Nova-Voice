# Frontend Application - Nova Voice

Electron-based desktop application for real-time speech-to-text and translation with voice typing and live subtitles.

## 🚀 Quick Start

### Prerequisites
- **Node.js 18+**
- **Backend services running** (see backend README)

### Installation & Running
```bash
# Install dependencies
npm install

# Development (with hot reload)
npm run dev

# Build and run in Electron
npm run build && npm run electron

# Or use the convenience script
npm run dev-full
```

### Default Connections
- **Gateway**: `ws://localhost:5026`
- **Backend**: `http://localhost:8080`

## 🎮 Usage

### Voice Typing Mode
1. Click the **"Voice Typing"** button
2. Select your **audio source** (microphone/system audio)
3. Choose **source language** for transcription
4. Start speaking - text appears automatically in your active application

### Live Subtitles Mode
1. Click the **"Live Subtitle"** button
2. A **transparent overlay** appears at the bottom of your screen
3. Shows both **transcription** and **translation** in real-time
4. **Click-through design** - doesn't interfere with other applications

### Keyboard Shortcuts
- **`Win+Alt+V`**: Toggle voice typing mode
- **`Win+Alt+L`**: Toggle live subtitles mode
- **`Win+Alt+H`**: Hide application window

## 📚 Documentation

- **[Component Architecture](docs/COMPONENT_ARCHITECTURE.md)** - React components and hooks
- **[Electron Integration](docs/ELECTRON_INTEGRATION.md)** - Main/renderer processes
- **[WebSocket Client](docs/WEBSOCKET_CLIENT.md)** - Backend communication
- **[Audio Management](docs/AUDIO_MANAGEMENT.md)** - Audio capture and processing
- **[Live Subtitles](docs/LIVE_SUBTITLES.md)** - Subtitle overlay functionality
