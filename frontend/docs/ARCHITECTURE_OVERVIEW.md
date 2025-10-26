# Nova Voice - Technical Documentation

## Overview

Nova Voice is an open-source real-time speech-to-text and translation desktop application built with Next.js, React, and Electron. It provides voice typing and live subtitle functionality with AI-powered translation capabilities. The application communicates with a Python-based backend gateway service via WebSocket for speech-to-text and translation processing.

**Key Changes for Open-Source Version:**
- Removed all authentication/OAuth flows
- Simplified architecture with custom hooks and services
- Default localhost connectivity (no token required)
- Clean, modular codebase for contributors
- Environment-based configuration

## Architecture

### Core Technologies

- **Frontend Framework**: Next.js 15.2.4 with React 19
- **Desktop Wrapper**: Electron 31.7.7
- **Styling**: Tailwind CSS 4.1.9 with shadcn/ui components
- **Language**: TypeScript 5.x
- **Audio Processing**: Web Audio API with custom audio recorder
- **Build Tool**: Next.js static export for Electron packaging

### Application Structure

```
Nova-UI/
├── app/                          # Next.js App Router
│   ├── layout.tsx               # Root layout with theme provider
│   ├── page.tsx                 # Main application component
│   └── globals.css              # Global styles with Tailwind
├── components/                   # React components
│   ├── ui/                      # shadcn/ui component library
│   │   ├── button.tsx           # Reusable button component
│   │   └── select.tsx           # Dropdown select component
│   ├── audio-device-selector.tsx # Audio input device selector
│   └── theme-provider.tsx       # Theme context provider
├── lib/                         # Utility libraries
│   ├── audio-devices.ts         # Audio device management
│   ├── audio-recorder.ts        # Web Audio API recorder
│   └── utils.ts                 # Utility functions (cn helper)
├── electron/                    # Electron desktop application
│   ├── main.js                  # Main process (window management, WebSocket)
│   ├── preload.js               # Context bridge for secure IPC
│   ├── login-preload.js         # Login window preload script
│   ├── subtitle-preload.js      # Subtitle overlay preload script
│   ├── notification-preload.js  # Notification window preload script
│   └── login.html               # Login window HTML
├── types/                       # TypeScript type definitions
│   └── electron.d.ts            # Electron API type declarations
├── test_audio_listen/           # Standalone audio testing application
├── dist/                        # Electron build output
├── out/                         # Next.js static export output
├── package.json                 # Dependencies and scripts
├── tsconfig.json               # TypeScript configuration
├── next.config.mjs             # Next.js configuration
└── electron-builder.json       # Electron build configuration
```

## Key Components

### 1. Main Application (`app/page.tsx`)

The main application component (~280 lines) is now a clean, modular React component that composes custom hooks and reusable components:

- **Hook-based Architecture**: Uses custom hooks for state management and side effects
- **Component Composition**: Built from smaller, focused components
- **Simplified Logic**: Removed authentication and complex state management
- **Real-time Communication**: WebSocket communication via connection hook
- **Audio Processing**: Delegated to audio recording hook

**Key Features:**
- Voice typing mode (Win+Alt+V): Simulates typing by pasting transcribed text
- Live subtitle mode (Win+Alt+L): Displays real-time subtitles in overlay window
- Dynamic window sizing with smooth animations
- Global keyboard shortcuts for mode switching
- Clean error handling and user feedback

### 2. Custom Hooks Architecture

The application now uses a modern hook-based architecture for clean state management:

#### `useConnection.ts`
- **Purpose**: Manages WebSocket connection to gateway service
- **Features**: Connection state, mode switching, automatic reconnection
- **API**: `connect()`, `disconnect()`, `setMode()`, connection status

#### `useAudioRecording.ts`
- **Purpose**: Wraps audio recorder with device management
- **Features**: Recording state, audio level monitoring, device selection
- **API**: `startRecording()`, `stopRecording()`, device management

#### `useShortcuts.ts`
- **Purpose**: Handles global keyboard shortcuts from Electron
- **Features**: Shortcut registration, action dispatching
- **API**: Event listener setup, action callbacks

#### `useWindowSizing.ts`
- **Purpose**: Manages dynamic window resizing based on UI state
- **Features**: ResizeObserver integration, dropdown height calculations
- **API**: Refs for components, sizing state, dropdown controls

### 3. Services Layer

#### `gateway.ts`
- **Purpose**: Thin wrapper around Electron API for gateway operations
- **Features**: Unified API for connect/send/setMode/updateLanguages/startOver
- **Benefits**: Centralized gateway communication, type safety

#### `config.ts`
- **Purpose**: Environment-based configuration management
- **Features**: Default localhost URLs, environment variable overrides
- **API**: `config.gatewayUrl`, `config.backendUrl`, `config.debug`

#### `log.ts`
- **Purpose**: Centralized logging utility
- **Features**: Debug flag support, multiple log levels
- **API**: `log.debug()`, `log.info()`, `log.warn()`, `log.error()`

### 4. Audio Device Management (`lib/audio-devices.ts`)

A singleton class that handles audio device enumeration and stream management:

- **Device Enumeration**: Filters out virtual audio devices and categorizes into input/output
- **Permission Management**: Handles microphone permission requests
- **System Audio Capture**: Special handling for Windows loopback audio via `getDisplayMedia()`
- **Device Filtering**: Aggressive filtering to show only physical microphones, avoiding virtual devices

**Categories:**
- **System Audio**: Special "system-audio" device for capturing desktop audio
- **Input Devices**: Physical microphones with virtual device filtering

### 5. Audio Recorder (`lib/audio-recorder.ts`)

Web Audio API-based real-time audio processing:

- **Audio Context**: 16kHz sample rate, mono channel
- **Script Processor Node**: Real-time audio data processing (4096 buffer size)
- **Format Conversion**: Float32 → Int16 conversion for server transmission
- **Audio Level Monitoring**: RMS calculation for visual feedback
- **Error Handling**: Comprehensive error handling for various failure modes

### 6. Control Components

The UI is now split into modular control components for better maintainability:

#### `ModeButtons.tsx`
- **Purpose**: Voice typing and live subtitle mode toggles
- **Features**: Visual state indicators, keyboard shortcut hints
- **Props**: Active states, toggle handlers

#### `LangSelectors.tsx`
- **Purpose**: Source and target language dropdowns
- **Features**: Dynamic window sizing, dropdown state management
- **Props**: Language values, change handlers, dropdown controls

#### `StatusIndicator.tsx`
- **Purpose**: Real-time connection and recording status display
- **Features**: Color-coded status, activity animations
- **States**: Inactive, Connected, Listening, Connecting

#### `TopBar.tsx`
- **Purpose**: Settings panel, hide window, and quit application buttons
- **Features**: Quick actions, settings toggle
- **Props**: Settings state, action handlers

#### `SettingsPanel.tsx`
- **Purpose**: Keybind configuration and device settings
- **Features**: Audio device selection, keyboard shortcut inputs
- **Props**: Current settings, change handlers

### 7. Electron Main Process (`electron/main.js`)

The Electron main process (~600 lines, simplified) handles:

- **Window Management**: Main window, subtitle overlay, and notifications (no login/auth)
- **WebSocket Client**: Direct connection to gateway service (no authentication)
- **Audio Streaming**: Real-time audio data transmission to backend
- **IPC Communication**: Secure inter-process communication with renderer
- **System Integration**: Native OS features (clipboard, typing simulation)

**Windows Created:**
- **Main Window**: Primary application interface (opens directly)
- **Subtitle Window**: Fullscreen overlay for live subtitles (click-through)
- **Notification Window**: Temporary status notifications

**Key Changes:**
- Removed all OAuth/authentication logic
- Simplified startup (no login window, direct main window)
- Default localhost gateway connection
- Environment variable configuration

## Technical Features

### Real-time Audio Processing Pipeline

1. **Device Selection**: User selects microphone or system audio
2. **Permission Request**: Automatic permission handling
3. **Audio Capture**: Web Audio API captures raw audio data
4. **Format Conversion**: Float32 samples → Int16 for transmission
5. **WebSocket Streaming**: Binary audio data sent to gateway
6. **Speech Recognition**: Backend processes audio and returns transcription
7. **Translation**: Optional language translation
8. **Output**: Text displayed via typing simulation or subtitle overlay

### Window Management System

- **Dynamic Sizing**: Window height adjusts based on UI state (settings panel, dropdowns)
- **Smooth Animations**: CSS Grid animations for expanding/collapsing content
- **Always-on-Top**: Configurable window positioning for accessibility
- **Transparent Backgrounds**: Glassmorphism design with backdrop blur

### Typing Simulation

Uses the `robotjs` library to simulate keyboard input:

- **Text Pasting**: Uses Ctrl+V to paste transcribed text
- **Smart Throttling**: Prevents text flooding with timing controls
- **Undo Management**: Handles text replacement by undoing previous paste
- **Separator Handling**: Adds spaces between utterances

### Subtitle Overlay System

The live subtitle feature creates a transparent, always-on-top window that displays real-time transcription and translation:

#### Window Management
- **Secondary Window**: Separate Electron window for subtitle overlay
- **Transparent Background**: CSS backdrop-blur for glassmorphism effect
- **Always-on-Top**: Stays visible above all other applications
- **Click-through**: Ignores mouse events to avoid interfering with other apps
- **Positioning**: Bottom-aligned, full-width display (typically 140px height)

#### IPC Communication
- **Window Creation**: Main process creates subtitle window when switching to subtitle mode
- **Text Updates**: IPC messages send transcription and translation updates
- **Dual Display**: Shows both original transcription and translated text
- **Text Cropping**: Displays last 85 characters to fit overlay width

#### Technical Implementation
```javascript
// Main process - subtitle window creation
const subtitleWindow = new BrowserWindow({
  width: screenWidth,
  height: 140,
  frame: false,
  transparent: true,
  alwaysOnTop: true,
  skipTaskbar: true,        // Hidden from taskbar
  focusable: false,         // Click-through enabled
  // Positioned at screen bottom
})
```

#### Text Update Flow
1. **Transcription Received**: Backend sends transcription via WebSocket
2. **IPC Message**: Main process forwards to subtitle window
3. **DOM Update**: Subtitle window updates text content
4. **Visual Display**: Text appears in overlay bubbles

### Security Architecture

- **Context Isolation**: Electron renderer processes isolated from Node.js APIs
- **Preload Scripts**: Secure IPC bridge with explicit API exposure
- **Permission Model**: Granular permission requests for audio access
- **No Node Integration**: Renderer processes cannot access Node.js directly

## Build and Deployment

### Development Workflow

```bash
# Install dependencies
npm install

# Development mode (Next.js dev server)
npm run dev

# Build Next.js static export (required for Electron)
npm run build

# Run in Electron (requires build + running gateway)
npm run electron

# Package Electron app for distribution
npm run electron-build
```

### Quick Start for Contributors

1. **Start Backend Gateway**: Ensure your backend gateway is running on `localhost:8081`
2. **Build Frontend**: `npm run build` (creates static export)
3. **Run Electron**: `npm run electron` (opens app directly, no login required)
4. **Development**: Use `npm run dev` for hot-reload during UI development

### Environment Configuration

Override default localhost URLs with environment variables:

```bash
# Custom gateway URL
GATEWAY_URL=wss://my-gateway.com npm run electron

# Custom backend URL
BACKEND_URL=https://my-api.com npm run electron

# Enable debug logging
DEBUG=true npm run electron
```

### Build Configuration

- **Next.js**: Configured for static export (`output: 'export'`) for Electron compatibility
- **Electron Builder**: Cross-platform packaging with custom build scripts
- **TypeScript**: Strict mode with path aliases (`@/*`)
- **Tailwind CSS**: Custom design system with CSS variables

### Dependencies

**Core UI Libraries:**
- Radix UI: Complete component primitive library
- Tailwind CSS: Utility-first CSS framework
- Lucide React: Icon library
- Next Themes: Dark/light theme support

**Audio Processing:**
- Web Audio API (native browser API)
- Custom audio recorder implementation
- Device enumeration via MediaDevices API

**Desktop Integration:**
- Electron: Cross-platform desktop application framework
- RobotJS: Native system automation (typing simulation)
- WebSocket: Real-time communication with backend

## Testing and Development Tools

### Test Audio Listen (`test_audio_listen/`)

A standalone Electron application for audio capture testing:

- **Purpose**: Prototype and test audio device enumeration and capture
- **Technology**: Separate Vite + React + Electron app
- **Features**: Windows Core Audio API integration via native addon
- **Native Addon**: C++ module using Windows MMDevice API for accurate device enumeration

**Key Differences from Main App:**
- Separate build system (Vite vs Next.js)
- Native C++ addon for Windows audio APIs
- Simplified UI focused on audio testing
- Not integrated with speech recognition backend

## Configuration and Customization

### Environment Variables

- `ELECTRON_DEBUG=1`: Enables DevTools in Electron windows
- `NODE_ENV`: Controls build behavior and logging

### Build-time Configuration

- **Electron Command Line Switches**: System audio capture and GPU acceleration settings
- **Window Properties**: Size, transparency, positioning, and behavior flags
- **Protocol Interception**: Custom file serving for static assets

### Runtime Configuration

- **Language Pairs**: Configurable source/target languages
- **Keyboard Shortcuts**: Customizable hotkeys for mode switching
- **Audio Settings**: Device selection and audio processing parameters

## Performance Considerations

### Audio Processing
- **Sample Rate**: 16kHz optimized for speech recognition accuracy
- **Buffer Size**: 4096 samples for low-latency processing
- **Compression**: No audio compression - raw PCM data transmission
- **Backpressure Handling**: WebSocket buffer monitoring to prevent overflow

### UI Performance
- **Virtual DOM**: React's efficient rendering system
- **CSS Animations**: Hardware-accelerated transitions
- **Window Resizing**: Optimized resize operations with debouncing
- **Memory Management**: Proper cleanup of audio contexts and media streams

### System Integration
- **Clipboard Operations**: Efficient text insertion via system clipboard
- **Typing Simulation**: Native OS integration for realistic text input
- **Overlay Rendering**: Hardware-accelerated transparent windows

## Known Limitations and Considerations

### Platform Support
- **Primary Platform**: Windows 10/11 (optimized for Windows audio APIs)
- **Audio Capture**: System audio capture requires Windows loopback support
- **Permissions**: OS-level permission prompts for microphone access

### Audio Quality
- **Sample Rate**: Fixed at 16kHz for backend compatibility
- **Channel Configuration**: Mono audio (single channel)
- **Format**: 16-bit PCM for transmission efficiency

### UI Constraints
- **Window Management**: Dynamic sizing may cause brief layout shifts
- **Transparency**: Requires compatible graphics drivers
- **Always-on-Top**: May interfere with fullscreen applications

## 📚 Detailed Documentation

For in-depth information on specific components and features, see:

### Architecture & Components
- **[COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md)** - Component patterns, custom hooks, and state management
- **[ELECTRON_INTEGRATION.md](ELECTRON_INTEGRATION.md)** - Main/renderer processes, IPC communication, and security

### Features & Functionality
- **[WEBSOCKET_CLIENT.md](WEBSOCKET_CLIENT.md)** - Real-time backend communication and message formats
- **[AUDIO_MANAGEMENT.md](AUDIO_MANAGEMENT.md)** - Audio capture, device selection, and processing pipeline
- **[LIVE_SUBTITLES.md](LIVE_SUBTITLES.md)** - Subtitle overlay functionality and configuration
- **[VOICE_TYPING_ENGINE.md](VOICE_TYPING_ENGINE.md)** - Voice typing simulation algorithm and text processing

### Development & Deployment
- **[DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md)** - Development workflow, hot reload, and debugging
- **[CONFIGURATION.md](CONFIGURATION.md)** - Environment variables, build settings, and runtime options
- **[BUILD_DEPLOYMENT.md](BUILD_DEPLOYMENT.md)** - Packaging, cross-platform builds, and distribution

## Future Enhancements

### Planned Features
- **AI Mode Integration**: Advanced AI-powered features
- **Multi-language Support**: Expanded language pair options
- **Audio Enhancement**: Noise reduction and echo cancellation
- **Customizable UI**: Theming and layout options

### Technical Improvements
- **Performance Optimization**: Reduced latency and memory usage
- **Cross-platform Support**: macOS and Linux compatibility
- **Advanced Audio Processing**: Better device detection and audio quality
- **Plugin Architecture**: Extensible feature system

---

This documentation provides a comprehensive overview of the Nova UI technical architecture. The application represents a sophisticated integration of modern web technologies with desktop system capabilities, enabling real-time speech processing and translation functionality.
