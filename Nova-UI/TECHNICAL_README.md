# Nova UI - Technical Documentation

## Overview

Nova UI is a sophisticated real-time speech translation desktop application built with Next.js, React, and Electron. It provides voice typing and live subtitle functionality with AI-powered translation capabilities. The application communicates with a Python-based backend gateway service via WebSocket for speech-to-text and translation processing.

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

The main application component (~1020 lines) is a comprehensive React component that manages:

- **State Management**: Complex state for connection status, audio recording, UI modes, and device selection
- **Real-time Communication**: WebSocket communication with backend gateway
- **Audio Processing**: Integration with custom audio recorder and device manager
- **Window Management**: Dynamic window resizing based on UI state
- **Mode Switching**: Voice typing vs live subtitle modes with keyboard shortcuts

**Key Features:**
- Voice typing mode (Ctrl+V): Simulates typing by pasting transcribed text via clipboard
- Live subtitle mode (Ctrl+L): Displays real-time subtitles in overlay window
- AI mode (Ctrl+A): Placeholder for future AI features
- Dynamic window sizing with smooth animations
- Permission handling for microphone and system audio access

### 2. Audio Device Management (`lib/audio-devices.ts`)

A singleton class that handles audio device enumeration and stream management:

- **Device Enumeration**: Filters out virtual audio devices and categorizes into input/output
- **Permission Management**: Handles microphone permission requests
- **System Audio Capture**: Special handling for Windows loopback audio via `getDisplayMedia()`
- **Device Filtering**: Aggressive filtering to show only physical microphones, avoiding virtual devices

**Categories:**
- **System Audio**: Special "system-audio" device for capturing desktop audio
- **Input Devices**: Physical microphones with virtual device filtering

### 3. Audio Recorder (`lib/audio-recorder.ts`)

Web Audio API-based real-time audio processing:

- **Audio Context**: 16kHz sample rate, mono channel
- **Script Processor Node**: Real-time audio data processing (4096 buffer size)
- **Format Conversion**: Float32 → Int16 conversion for server transmission
- **Audio Level Monitoring**: RMS calculation for visual feedback
- **Error Handling**: Comprehensive error handling for various failure modes

### 4. Audio Device Selector (`components/audio-device-selector.tsx`)

React component for selecting audio input sources:

- **Device Categorization**: Separate UI for system audio vs microphone devices
- **Real-time Updates**: Device change detection and automatic refresh
- **Permission Dialogs**: Guided system audio capture setup
- **Responsive Design**: Adapts to different dropdown contexts

### 5. Electron Main Process (`electron/main.js`)

The Electron main process (~1150 lines) handles:

- **Window Management**: Multiple windows (main, login, subtitle overlay, notifications)
- **WebSocket Client**: Connection to Python gateway service
- **Audio Streaming**: Real-time audio data transmission to backend
- **IPC Communication**: Secure inter-process communication with renderer
- **System Integration**: Native OS features (clipboard, typing simulation)

**Windows Created:**
- **Main Window**: Primary application interface
- **Login Window**: Authentication screen
- **Subtitle Window**: Fullscreen overlay for live subtitles (click-through)
- **Notification Window**: Temporary status notifications

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

- **Dual Subtitle Mode**: Shows both transcription and translation simultaneously
- **Text Cropping**: Displays last 85 characters to fit overlay width
- **Click-through**: Overlay ignores mouse events, allowing interaction with underlying applications
- **Positioning**: Bottom-aligned, full-width display

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

# Electron development
npm run electron

# Build Next.js static export
npm run build

# Package Electron app
npm run electron-build
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
