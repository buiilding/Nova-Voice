# Frontend Application - Nova Voice

Electron desktop client with a simplified Linux UI focused on voice typing only.

## 🚀 Quick Start

### Prerequisites
- **Node.js 18+**
- **Backend services running** (see backend README)
- **Linux desktop session** (voice typing automation uses `robotjs`)

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

### Simple Linux Voice Typing Flow
1. Start backend services first.
2. Open frontend (`npm run build && npm run electron`).
3. Pick microphone input.
4. Pick source/target language (same source+target disables translation).
5. Click **Start Voice Typing**.
6. Speak while cursor is focused in target app.

Notes:
- Live subtitle mode is disabled in Linux simple UI mode.
- Global shortcuts are skipped on Linux simple UI mode.
- If startup shows `robotjs is unavailable`, run dependency rebuild (`npm install` / `npm run postinstall`) and retry.

## 📚 Documentation

- **[Component Architecture](docs/COMPONENT_ARCHITECTURE.md)** - React components and hooks
- **[Electron Integration](docs/ELECTRON_INTEGRATION.md)** - Main/renderer processes
- **[WebSocket Client](docs/WEBSOCKET_CLIENT.md)** - Backend communication
- **[Audio Management](docs/AUDIO_MANAGEMENT.md)** - Audio capture and processing
