# Frontend Configuration Guide

Complete reference for environment variables, build settings, and runtime configuration in the Nova Voice frontend application.

## 📋 Configuration Overview

The frontend supports configuration through environment variables, build-time settings, and runtime options. Configuration is layered to support different deployment scenarios.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Environment    │────│   Build-time    │────│   Runtime       │
│  Variables      │    │   Settings      │    │   Options       │
│                 │    │                 │    │                 │
│ • Backend URLs  │    │ • Bundle opts   │    │ • Audio devices │
│ • Debug flags   │    │ • Feature flags │    │ • Shortcuts     │
│ • Feature toggles│    │ • API endpoints│    │ • UI settings   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🌐 Environment Variables

### Backend Connection

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_URL` | `ws://localhost:5026` | WebSocket URL for gateway service |
| `BACKEND_URL` | `http://localhost:8080` | HTTP URL for backend API (future use) |

### Development & Debugging

| Variable | Default | Description |
|----------|---------|-------------|
| `NODE_ENV` | `production` | Environment mode (`development`, `production`) |
| `DEBUG` | `false` | Enable debug logging |
| `ELECTRON_DEBUG` | `false` | Enable Electron DevTools |

### Build Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `` | Public API URL (exposed to browser) |
| `NEXT_PUBLIC_GATEWAY_URL` | `` | Public WebSocket URL (exposed to browser) |
| `NEXT_PUBLIC_DEBUG` | `false` | Enable client-side debug logging |

## 🔧 Runtime Configuration

### Audio Settings

```typescript
// Audio constraints (configured in audio-recorder.ts)
const AUDIO_CONSTRAINTS = {
  echoCancellation: false,    // Keep original audio quality
  noiseSuppression: false,    // Preserve audio fidelity
  autoGainControl: true,      // Normalize volume levels
  sampleRate: 16000,          // Optimized for speech recognition
  channelCount: 1,            // Mono audio
  latency: 0.01               // 10ms latency target
}
```

### WebSocket Configuration

```typescript
// Connection settings (configured in Electron main process)
const WEBSOCKET_CONFIG = {
  url: process.env.GATEWAY_URL || 'ws://localhost:5026',
  reconnectInterval: 1000,      // Initial reconnect delay
  maxReconnectAttempts: 10,     // Maximum reconnection attempts
  heartbeatInterval: 30000,     // Connection health check
  messageTimeout: 5000         // Message response timeout
}
```

### UI Configuration

```typescript
// Window settings (configured in electron/main.js)
const WINDOW_CONFIG = {
  width: 1050,
  height: 600,
  minWidth: 800,
  minHeight: 500,
  frame: false,                // Frameless design
  transparent: true,           // Glassmorphism effect
  alwaysOnTop: false,          // User configurable
  resizable: true,
  maximizable: false,          // Fixed size application
  fullscreenable: false
}
```

## ⚙️ Build-Time Configuration

### Next.js Configuration

```javascript
// next.config.mjs
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export for Electron compatibility
  output: 'export',
  trailingSlash: true,
  images: {
    unoptimized: true  // Required for static export
  },

  // Environment variables exposed to browser
  env: {
    NEXT_PUBLIC_GATEWAY_URL: process.env.NEXT_PUBLIC_GATEWAY_URL,
    NEXT_PUBLIC_DEBUG: process.env.NEXT_PUBLIC_DEBUG
  },

  // Webpack configuration for Electron
  webpack: (config, { isServer }) => {
    if (!isServer) {
      // Browser-specific optimizations
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        path: false
      }
    }
    return config
  }
}

export default nextConfig
```

### Electron Builder Configuration

```javascript
// electron-builder.json
{
  "appId": "com.nova.voice",
  "productName": "Nova Voice",
  "directories": {
    "output": "dist"
  },
  "files": [
    "out/**/*",           // Next.js static export
    "electron/**/*",      // Electron main process files
    "node_modules/**/*",
    "package.json"
  ],
  "mac": {
    "target": "dmg",
    "category": "public.app-category.productivity"
  },
  "win": {
    "target": "nsis",
    "icon": "public/favicon.ico"
  },
  "linux": {
    "target": "AppImage",
    "category": "Utility"
  },
  "nsis": {
    "oneClick": false,
    "perMachine": false,
    "allowToChangeInstallationDirectory": true
  }
}
```

### TypeScript Configuration

```json
// tsconfig.json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "ES6"],
    "allowJs": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noFallthroughCasesInSwitch": true,
    "module": "esnext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    },
    "incremental": true,
    "tsBuildInfoFile": ".next/cache/tsconfig.tsbuild.json"
  },
  "include": [
    "next-env.d.ts",
    "**/*.ts",
    "**/*.tsx",
    "types/**/*"
  ],
  "exclude": [
    "node_modules",
    "out",
    "dist"
  ]
}
```

## 🎨 Styling Configuration

### Tailwind CSS Configuration

```javascript
// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
    './app/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Custom color palette for glassmorphism
        slate: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617'
        }
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography')
  ],
}
```

### CSS Custom Properties

```css
/* globals.css */
:root {
  /* Glassmorphism variables */
  --glass-bg: rgba(30, 41, 59, 0.7);
  --glass-border: rgba(71, 85, 105, 0.3);
  --glass-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);

  /* Animation durations */
  --transition-fast: 150ms;
  --transition-normal: 300ms;
  --transition-slow: 500ms;

  /* Spacing scale */
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 0.75rem;
  --space-lg: 1rem;
  --space-xl: 1.5rem;
}
```

## 🔒 Security Configuration

### Content Security Policy

```javascript
// electron/main.js
const mainWindow = new BrowserWindow({
  webPreferences: {
    // Security hardening
    nodeIntegration: false,
    contextIsolation: true,
    enableRemoteModule: false,

    // CSP headers
    webSecurity: true,

    // Additional security
    allowRunningInsecureContent: false,
    experimentalFeatures: false
  }
})
```

### IPC Security

```typescript
// Preload script security
contextBridge.exposeInMainWorld('electronAPI', {
  // Only expose necessary APIs
  connectGateway: () => ipcRenderer.invoke('connect-gateway'),
  sendAudioData: (data: Float32Array, rate: number) => {
    // Input validation
    if (!isValidAudioData(data, rate)) {
      throw new Error('Invalid audio data')
    }
    return ipcRenderer.invoke('send-audio-data', data, rate)
  }
})

// Input validation function
function isValidAudioData(data: Float32Array, rate: number): boolean {
  return (
    ArrayBuffer.isView(data) &&
    data.length > 0 &&
    data.length < MAX_AUDIO_BUFFER_SIZE &&
    rate >= 8000 &&
    rate <= 48000
  )
}
```

## 🚀 Performance Configuration

### Bundle Optimization

```javascript
// next.config.mjs - Bundle analysis
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
})

module.exports = withBundleAnalyzer({
  // Bundle splitting
  experimental: {
    optimizePackageImports: ['lucide-react', '@radix-ui/react-select']
  },

  // Compression
  compress: true,

  // Image optimization
  images: {
    formats: ['image/webp', 'image/avif'],
    deviceSizes: [640, 750, 828, 1080, 1200],
  }
})
```

### Electron Performance

```javascript
// electron/main.js - Performance optimizations
app.commandLine.appendSwitch('disable-background-timer-throttling')
app.commandLine.appendSwitch('disable-renderer-backgrounding')
app.commandLine.appendSwitch('disable-backgrounding-occluded-windows')

// GPU acceleration for better performance
app.commandLine.appendSwitch('ignore-gpu-blacklist')
app.commandLine.appendSwitch('enable-gpu-rasterization')
app.commandLine.appendSwitch('enable-zero-copy')
```

## 🐛 Debugging Configuration

### Development Debug Flags

```bash
# Enable various debug modes
DEBUG=true npm run electron          # General debug logging
ELECTRON_DEBUG=1 npm run electron    # Electron DevTools
DEBUG_WEBSOCKET=true npm run electron # WebSocket debug logs
DEBUG_AUDIO=true npm run electron     # Audio processing logs
```

### Logging Configuration

```typescript
// lib/log.ts
class Logger {
  private debugEnabled: boolean

  constructor() {
    this.debugEnabled = process.env.DEBUG === 'true' ||
                       process.env.NODE_ENV === 'development'
  }

  debug(message: string, ...args: any[]) {
    if (this.debugEnabled) {
      console.debug(`[DEBUG] ${message}`, ...args)
    }
  }

  info(message: string, ...args: any[]) {
    console.info(`[INFO] ${message}`, ...args)
  }

  warn(message: string, ...args: any[]) {
    console.warn(`[WARN] ${message}`, ...args)
  }

  error(message: string, ...args: any[]) {
    console.error(`[ERROR] ${message}`, ...args)
  }
}

export const log = new Logger()
```

### Error Boundaries

```typescript
// components/ErrorBoundary.tsx
class ErrorBoundary extends Component {
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details
    log.error('React Error Boundary caught an error:', error, errorInfo)

    // Send to error reporting service (future)
    if (process.env.NODE_ENV === 'production') {
      // reportError(error, errorInfo)
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <button onClick={() => window.location.reload()}>
            Reload Application
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
```

## 📊 Feature Flags

### Runtime Feature Toggles

```typescript
// lib/config.ts
export const config = {
  // Feature flags
  features: {
    voiceTyping: true,
    liveSubtitles: true,
    audioDeviceSelection: true,
    globalShortcuts: true,
    settingsPanel: true
  },

  // Experimental features
  experimental: {
    advancedAudioProcessing: false,
    aiFeatures: false,
    multiLanguage: false
  },

  // URLs
  gatewayUrl: process.env.GATEWAY_URL || 'ws://localhost:5026',
  backendUrl: process.env.BACKEND_URL || 'http://localhost:8080',

  // Debug settings
  debug: process.env.DEBUG === 'true',
  electronDebug: process.env.ELECTRON_DEBUG === 'true'
}
```

### Build-Time Feature Flags

```javascript
// next.config.mjs
const features = {
  VOICE_TYPING: true,
  LIVE_SUBTITLES: true,
  AUDIO_DEVICES: true,
  SHORTCUTS: true
}

module.exports = {
  env: {
    // Expose feature flags to client
    ...features
  },

  webpack: (config) => {
    // Dead code elimination based on features
    if (!features.LIVE_SUBTITLES) {
      config.plugins.push(
        new webpack.IgnorePlugin({
          resourceRegExp: /subtitle/,
        })
      )
    }
    return config
  }
}
```

## 🧪 Testing Configuration

### Test Environment Setup

```javascript
// jest.config.js
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/$1',
    '^electron$': '<rootDir>/__mocks__/electron.js'
  },
  testMatch: [
    '<rootDir>/**/*.test.ts',
    '<rootDir>/**/*.test.tsx'
  ],
  collectCoverageFrom: [
    'components/**/*.{ts,tsx}',
    'hooks/**/*.{ts,tsx}',
    'lib/**/*.{ts,tsx}',
    '!**/*.d.ts'
  ]
}
```

### Electron Testing

```javascript
// jest.setup.js
// Mock Electron APIs for testing
global.window.electronAPI = {
  connectGateway: jest.fn(),
  sendAudioData: jest.fn(),
  setMode: jest.fn(),
  // ... other mocks
}
```

## 📋 Configuration Checklist

### Development Setup
- [ ] Environment variables configured in `.env`
- [ ] Debug flags set appropriately
- [ ] Backend URLs pointing to correct services
- [ ] Feature flags enabled for testing

### Build Configuration
- [ ] Next.js config optimized for Electron
- [ ] TypeScript strict mode enabled
- [ ] Bundle analyzer configured for performance monitoring
- [ ] Electron builder targets set for target platforms

### Production Deployment
- [ ] Environment variables override defaults
- [ ] Debug flags disabled
- [ ] Production backend URLs configured
- [ ] Bundle optimizations enabled
- [ ] Security hardening applied

### Security
- [ ] CSP headers configured
- [ ] IPC exposure limited to necessary APIs
- [ ] Input validation on all external inputs
- [ ] Error messages don't leak sensitive information

---

**Configuration is layered to support development, testing, and production deployments with appropriate security and performance settings for each environment.**
