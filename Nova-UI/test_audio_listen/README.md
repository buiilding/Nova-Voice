# Audio Listener - Electron + React App

A React app wrapped in Electron that can capture system audio and microphone input using Windows Core Audio MMDevice API.

## Features

- **Microphone Capture**: Select from available microphone devices
- **System Audio Capture**: Capture system audio via Windows loopback (getDisplayMedia)
- **Windows Core Audio Integration**: Uses native MMDevice API to enumerate audio endpoints exactly like Windows Settings
- **Real-time Audio Meters**: Visual feedback for audio levels
- **One-time Permissions**: OS-level prompts only appear once

## Prerequisites

- Windows 10/11
- Node.js 18+ 
- Visual Studio Build Tools (for native addon compilation)
- Python 3.x (for node-gyp)

## Installation

1. **Install Visual Studio Build Tools**:
   ```bash
   # Download and install Visual Studio Build Tools 2022
   # Include "Desktop development with C++" workload
   ```

2. **Install Python** (if not already installed):
   ```bash
   # Download Python 3.x from python.org
   ```

3. **Install dependencies**:
   ```bash
   npm install
   ```

4. **Build native addon**:
   ```bash
   cd native
   npm run build
   cd ..
   ```

## Development

```bash
npm run dev
```

This will:
- Start Vite dev server on port 5173
- Wait for server to be ready
- Launch Electron app

## Building

```bash
npm run build
npm run start:prod
```

## How It Works

### Windows Core Audio Integration

The app uses a native Node.js addon (`native/audio-endpoints.cpp`) that directly calls Windows Core Audio MMDevice API to enumerate audio endpoints. This provides the same device names as Windows Settings, avoiding the duplicate entries you see with `navigator.mediaDevices.enumerateDevices()`.

### System Audio Capture

System audio is captured using `getDisplayMedia()` with Electron's `setDisplayMediaRequestHandler` to auto-approve the request and include loopback audio on Windows.

### Microphone Capture

Microphone input uses standard `getUserMedia()` with device selection from the Windows Core Audio enumeration.

## Troubleshooting

### Native Addon Build Issues

If you encounter build errors:

1. Ensure Visual Studio Build Tools are installed with C++ workload
2. Run `npm config set msvs_version 2022` 
3. Try `npm rebuild` in the native directory

### Audio Capture Issues

- Ensure microphone permissions are granted in Windows Settings
- For system audio, ensure "Allow apps to access your microphone" is enabled
- Some audio drivers may not support loopback capture

## Project Structure

```
├── electron/
│   ├── main.js          # Electron main process
│   └── preload.js       # Preload script with native API bridge
├── native/
│   ├── audio-endpoints.cpp  # Windows Core Audio native addon
│   ├── binding.gyp      # Build configuration
│   └── index.js         # JavaScript wrapper
├── src/
│   ├── renderer/
│   │   └── App.tsx      # React UI with audio capture
│   └── main.tsx         # React entry point
└── package.json
```
