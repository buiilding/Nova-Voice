# Development Setup Guide

Complete guide for setting up the development environment for the Nova Voice frontend application.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js UI    │────│ Electron Main   │────│   Backend       │
│   (React)       │    │   Process       │    │   Gateway       │
│                 │    │                 │    │ (WebSocket)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │
        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐
│   Custom Hooks  │    │ Audio Recording │
│   & Components  │    │   & WebSocket   │
└─────────────────┘    └─────────────────┘
```

## 🚀 Quick Development Start

### Prerequisites
- **Node.js 18+** (LTS recommended)
- **Backend Services** running (see backend docs)
- **Git** for version control
- **VS Code** or similar IDE with TypeScript support

### 1. Clone and Setup
```bash
git clone <repository-url>
cd realtime-speech-microservices/frontend
npm install
```

### 2. Start Development
```bash
# Start Next.js development server (hot reload)
npm run dev

# In another terminal, build and run Electron
npm run build && npm run electron
```

### 3. Verify Setup
- Next.js dev server: http://localhost:3000
- Electron app opens with control panel
- Backend gateway connection: `ws://localhost:5026`

## 🔧 Development Workflows

### Hot Reload Development (Recommended)
```bash
# Terminal 1: Next.js development server
npm run dev

# Terminal 2: Build and watch for changes
npm run build-watch

# Terminal 3: Run Electron app
npm run electron-dev
```

**Benefits:**
- ✅ Instant UI updates without rebuild
- ✅ Full TypeScript checking and error reporting
- ✅ Component hot module replacement
- ✅ Easy debugging with React DevTools

### Full Electron Development
```bash
# One-command development (requires backend running)
npm run dev-full

# Or manually:
npm run build
npm run electron
```

**Benefits:**
- ✅ Complete desktop app experience
- ✅ Audio recording and device selection
- ✅ WebSocket communication testing
- ✅ Production-like environment

### Backend Integration Testing
```bash
# Ensure backend is running first
cd ../backend/infra
make up

# Then start frontend
cd ../../frontend
npm run dev-full
```

## 🧪 Testing and Debugging

### Development Scripts
```bash
# Available npm scripts
npm run dev          # Next.js development server
npm run build        # Production build
npm run build-watch  # Watch mode build
npm run electron     # Run Electron app
npm run electron-dev # Electron with dev tools
npm run lint         # ESLint checking
npm run type-check   # TypeScript type checking
```

### Debugging Electron Apps
```bash
# Enable DevTools in Electron
ELECTRON_DEBUG=1 npm run electron

# Debug main process (add to main.js temporarily)
console.log('Debug main process');
require('electron').app.commandLine.appendSwitch('remote-debugging-port', '9222');

# Debug renderer process
# Open DevTools in Electron window (View → Toggle Developer Tools)
```

### Testing Audio Features
```bash
# Test audio device enumeration
npm run dev
# Open browser console and check:
navigator.mediaDevices.enumerateDevices()

# Test WebSocket connection
npm run dev
# Open browser console and check WebSocket logs
```

### Common Debug Commands
```bash
# Check Node.js version
node --version

# Check npm version
npm --version

# Clear npm cache
npm cache clean --force

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Check build output
ls -la out/
```

## 🏗️ Development Workflow

### Making Code Changes

1. **Edit React Components** in `src/components/`
2. **Update Custom Hooks** in `src/hooks/`
3. **Modify Electron Code** in `electron/`
4. **Hot reload happens automatically** (Next.js dev server)
5. **Rebuild for Electron** when changing electron code
6. **Test in Electron** for full functionality

### Adding New Features

1. **Create Component** in appropriate `components/` subdirectory
2. **Add Custom Hook** in `hooks/` for state management
3. **Update Types** in `types/electron.d.ts` for new APIs
4. **Add Electron API** in `electron/main.js` and `electron/preload.js`
5. **Test Integration** with backend services

### Code Organization
```
frontend/
├── components/          # React components
│   ├── ui/             # Reusable UI components
│   ├── control/        # Control panel components
│   └── settings/       # Settings components
├── hooks/              # Custom React hooks
├── lib/                # Utilities and services
├── electron/           # Electron main process
├── types/              # TypeScript definitions
└── app/                # Next.js pages and layout
```

## 🔧 Configuration for Development

### Environment Variables
```bash
# Override backend URLs
GATEWAY_URL=ws://localhost:5026
BACKEND_URL=http://localhost:8080

# Enable debugging
ELECTRON_DEBUG=1
DEBUG=true

# Development mode
NODE_ENV=development
```

### TypeScript Configuration
```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "jsx": "preserve",
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

### ESLint Configuration
```javascript
// .eslintrc.js
module.exports = {
  extends: [
    'next/core-web-vitals',
    '@typescript-eslint/recommended'
  ],
  rules: {
    // Custom rules for the project
  }
}
```

## 🚀 Building and Packaging

### Development Builds
```bash
# Quick build for testing
npm run build

# Build with watch mode
npm run build-watch

# Build for Electron
npm run build && npm run electron
```

### Production Builds
```bash
# Full production build
npm run build

# Package Electron app
npm run electron-build

# Output in dist/ directory
ls -la dist/
```

### Cross-Platform Builds
```bash
# Build for Windows (current)
npm run electron-build

# Build for all platforms (configure in electron-builder.json)
# Windows: .exe installer
# macOS: .dmg
# Linux: .AppImage
```

## 🐛 Troubleshooting

### Build Issues
```bash
# Clear Next.js cache
rm -rf .next out

# Clear Electron cache
rm -rf dist node_modules/.cache

# Rebuild native dependencies
npm rebuild
```

### Electron Issues
```bash
# Check Electron version
npx electron --version

# Run Electron directly for debugging
npx electron electron/main.js

# Check for conflicting processes
tasklist | findstr electron
```

### WebSocket Connection Issues
```bash
# Check backend is running
curl http://localhost:8080/health

# Check WebSocket port
netstat -ano | findstr 5026

# Test WebSocket connection manually
# Use browser console or tools like WebSocket King
```

### Audio Permission Issues
```bash
# Chrome audio settings
chrome://settings/content/microphone

# Windows audio settings
# Settings → Privacy → Microphone

# Test audio in browser
# Open http://localhost:3000 and check console for audio errors
```

## 🔄 Hot Reload Setup

### Next.js Hot Reload
- **Automatic**: Changes to React components hot reload
- **Fast Refresh**: Preserves component state during reloads
- **TypeScript**: Instant type checking and error reporting

### Electron Hot Reload
```javascript
// Add to electron/main.js for development
if (process.env.NODE_ENV === 'development') {
  // Reload on main process changes
  require('electron-reload')(path.join(__dirname, '..'), {
    electron: path.join(__dirname, '..', 'node_modules', '.bin', 'electron')
  });
}
```

## 📊 Performance Monitoring

### Development Metrics
```bash
# Bundle analyzer
npm install --save-dev @next/bundle-analyzer
npm run build:analyze

# Lighthouse for performance
# Use Chrome DevTools → Lighthouse

# React DevTools for component profiling
# Chrome extension for React performance monitoring
```

### Electron Performance
```bash
# Electron DevTools
# Open in Electron: View → Toggle Developer Tools

# Memory usage
# Chrome DevTools → Performance → Memory

# GPU usage
# Task Manager → GPU column
```

## 🧪 Testing Strategy

### Unit Tests
```bash
# Run tests
npm test

# Watch mode
npm run test:watch

# Coverage report
npm run test:coverage
```

### Integration Tests
```bash
# Test with backend
npm run test:e2e

# Manual testing checklist
- [ ] App starts without errors
- [ ] WebSocket connects to backend
- [ ] Audio devices are enumerated
- [ ] Voice typing works
- [ ] Live subtitles work
- [ ] Settings persist
```

### Cross-Platform Testing
- **Windows**: Primary development platform
- **macOS**: Test builds and audio handling
- **Linux**: Test builds and system compatibility

## 📚 Related Documentation

- **[QUICK_START.md](../QUICK_START.md)** - Get running in 5 minutes
- **[COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md)** - Component patterns and hooks
- **[ELECTRON_INTEGRATION.md](ELECTRON_INTEGRATION.md)** - Main/renderer processes
- **[AUDIO_MANAGEMENT.md](AUDIO_MANAGEMENT.md)** - Audio handling details
- **[BUILD_DEPLOYMENT.md](BUILD_DEPLOYMENT.md)** - Packaging and distribution

## 🆘 Getting Help

1. **Check the logs** - `npm run dev` for Next.js, Electron console for runtime
2. **Clear caches** - Delete `node_modules`, `.next`, `out`, `dist`
3. **Reinstall** - Fresh `npm install`
4. **Check versions** - Node.js, npm, Electron compatibility
5. **Test components** - Isolate issues to specific components

**Happy coding! 🎉**
