# Nova UI

A modern, Electron-based speech translation interface with voice typing, live subtitles, and AI-powered translation.

## Features

- **Voice Typing**: Real-time speech-to-text with automatic keyboard input
- **Live Subtitles**: On-screen subtitle overlay for real-time translation
- **AI Mode**: Advanced AI-powered translation and processing
- **Multi-language Support**: Support for multiple source and target languages
- **Audio Device Selection**: Choose between microphone input and system audio output

## Audio Device Selection

### Input Devices (Microphones)
- Standard microphone input devices
- Direct access through browser's `getUserMedia()` API
- No additional permissions required beyond microphone access

### Output Devices (System Audio)
- System audio output devices (speakers, headphones, etc.)
- Requires screen sharing permission through `getDisplayMedia()` API
- **Important**: When selecting an output device, you will be prompted to share a tab, window, or screen
- Choose the application or tab whose audio you want to capture
- This is a browser security limitation - direct system audio capture is not possible

### Troubleshooting Audio Issues

1. **Permission Denied**: Ensure microphone access is allowed in your browser settings
2. **No Audio Devices Found**: Check that your audio devices are properly connected and recognized by your system
3. **System Audio Not Working**: 
   - Make sure to select a tab/window when prompted for screen sharing
   - The audio will only capture from the selected source
   - Try selecting "Share entire screen" if you want to capture all system audio

## Development

### Prerequisites
- Node.js 18+
- npm or yarn

### Installation
```bash
npm install
```

### Development
```bash
npm run dev
```

### Build
```bash
npm run build
```

### Electron Development
```bash
npm run electron
```

### Package for Distribution
```bash
npm run dist
```

## Architecture

- **Frontend**: Next.js with TypeScript and Tailwind CSS
- **Desktop**: Electron for cross-platform desktop app
- **Audio Processing**: Web Audio API for real-time audio capture and processing
- **UI Components**: Radix UI primitives with custom styling

## License

Private - Nova Team