# Build and Deployment Guide

Complete guide for building, packaging, and distributing the Nova Voice frontend application across different platforms.

## 🏗️ Build System Overview

The frontend uses a multi-stage build process combining Next.js static export with Electron packaging.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Next.js       │────│   Electron      │────│   Distribution  │
│   Build         │    │   Packaging     │    │   Artifacts     │
│                 │    │                 │    │                 │
│ • Static Export │    │ • Cross-platform│    │ • .exe (Windows)│
│ • TypeScript    │    │ • Code signing  │    │ • .dmg (macOS)  │
│ • Optimization  │    │ • Auto-updates  │    │ • .AppImage     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 Prerequisites

### Development Environment
- **Node.js**: 18.0+ (LTS recommended)
- **npm**: 8.0+ or **yarn**: 1.22+
- **Git**: For version control
- **Python**: 3.8+ (for some build scripts)

### Platform-Specific Requirements

#### Windows
```powershell
# Windows Build Tools (run as Administrator)
npm install -g windows-build-tools
# or
npm install -g @vscode/windows-build-tools
```

#### macOS
```bash
# Xcode Command Line Tools
xcode-select --install

# If building for multiple architectures
sudo xcode-select -s /Applications/Xcode.app
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt-get install libnss3-dev libatk-bridge2.0-dev libdrm2 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libxss1 libasound2

# CentOS/RHEL/Fedora
sudo yum install libXScrnSaver GConf2 libnotify
```

## 🚀 Build Scripts

### Available Commands

```bash
# Development builds
npm run dev          # Next.js development server (hot reload)
npm run build        # Production Next.js build
npm run build-watch  # Watch mode for development

# Electron development
npm run electron     # Run Electron with current build
npm run electron-dev # Electron with DevTools enabled

# Production builds
npm run build        # Next.js static export (required for Electron)
npm run electron-build # Package Electron app for distribution
npm run dist         # Full production build pipeline
```

### Build Pipeline

```bash
# Complete production build
npm run build && npm run electron-build

# This executes:
# 1. Next.js static export (creates /out directory)
# 2. Electron packaging (creates /dist directory)
# 3. Cross-platform binaries
```

## ⚙️ Next.js Build Configuration

### Static Export Setup

```javascript
// next.config.mjs
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required for Electron compatibility
  output: 'export',

  // Static export requirements
  trailingSlash: true,
  skipTrailingSlashRedirect: true,
  distDir: 'out',

  // Image optimization disabled for static export
  images: {
    unoptimized: true,
    loader: 'custom'
  },

  // Environment variables for build
  env: {
    BUILD_TIME: new Date().toISOString(),
    VERSION: process.env.npm_package_version
  },

  // Bundle analysis (optional)
  ...(process.env.ANALYZE === 'true' && {
    bundleAnalyzer: {
      enabled: true,
      openAnalyzer: false
    }
  })
}

export default nextConfig
```

### Build Optimization

```javascript
// next.config.mjs - Advanced optimization
const nextConfig = {
  // Bundle splitting
  experimental: {
    optimizePackageImports: [
      'lucide-react',
      '@radix-ui/react-select',
      '@radix-ui/react-dialog'
    ]
  },

  // Compression
  compress: true,

  // Webpack optimizations
  webpack: (config, { dev, isServer }) => {
    if (!dev && !isServer) {
      // Production browser optimizations
      config.optimization.splitChunks.chunks = 'all'

      // Remove unused code
      config.optimization.usedExports = true

      // Minimize bundle size
      config.optimization.minimize = true
    }

    return config
  }
}
```

## 📦 Electron Packaging

### Electron Builder Configuration

```json
// electron-builder.json
{
  "appId": "com.nova.voice",
  "productName": "Nova Voice",
  "copyright": "Copyright © 2024 Nova Voice",

  "directories": {
    "output": "dist",
    "buildResources": "build"
  },

  "files": [
    "out/**/*",
    "electron/**/*",
    "node_modules/**/*",
    "package.json"
  ],

  "extraFiles": [
    {
      "from": "out/_next/static",
      "to": "resources/app.asar.unpacked/out/_next/static",
      "filter": ["**/*"]
    }
  ],

  "mac": {
    "target": [
      {
        "target": "dmg",
        "arch": ["x64", "arm64"]
      }
    ],
    "category": "public.app-category.productivity",
    "icon": "build/icon.icns",
    "hardenedRuntime": true,
    "gatekeeperAssess": false
  },

  "win": {
    "target": [
      {
        "target": "nsis",
        "arch": ["x64", "ia32"]
      }
    ],
    "icon": "build/icon.ico",
    "certificateFile": "certificates/win.p12",
    "certificatePassword": "${WIN_CERT_PASSWORD}",
    "verifyUpdateCodeSignature": false
  },

  "linux": {
    "target": [
      {
        "target": "AppImage",
        "arch": ["x64"]
      },
      {
        "target": "deb",
        "arch": ["x64"]
      }
    ],
    "icon": "build/icon.png",
    "category": "Utility"
  },

  "nsis": {
    "oneClick": false,
    "perMachine": true,
    "allowToChangeInstallationDirectory": true,
    "installerIcon": "build/icon.ico",
    "uninstallerIcon": "build/icon.ico",
    "installerHeaderIcon": "build/icon.ico",
    "createDesktopShortcut": true,
    "createStartMenuShortcut": true,
    "shortcutName": "Nova Voice"
  },

  "publish": {
    "provider": "github",
    "owner": "your-org",
    "repo": "nova-voice"
  }
}
```

### Build Scripts

```json
// package.json - build scripts
{
  "scripts": {
    "build": "next build",
    "build:analyze": "ANALYZE=true next build",
    "electron": "electron electron/main.js",
    "electron:pack": "electron-builder --dir",
    "electron:dist": "electron-builder",
    "electron:dist:win": "electron-builder --win",
    "electron:dist:mac": "electron-builder --mac",
    "electron:dist:linux": "electron-builder --linux",
    "dist": "npm run build && npm run electron:dist"
  }
}
```

## 🔐 Code Signing

### Windows Code Signing

```bash
# Install Windows SDK
# Download from: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/

# Sign executable
signtool sign /f certificate.p12 /p password /d "Nova Voice" /t http://timestamp.digicert.com dist/NovaVoice.exe
```

### macOS Code Signing

```bash
# Sign application
codesign --deep --force --verbose --sign "Developer ID Application: Your Name" dist/mac/NovaVoice.app

# Verify signature
codesign --verify --verbose dist/mac/NovaVoice.app
```

### Automated Code Signing

```javascript
// electron-builder.json - automated signing
{
  "win": {
    "certificateFile": "certificates/win.p12",
    "certificatePassword": "${WIN_CERT_PASSWORD}"
  },
  "mac": {
    "identity": "Developer ID Application: Your Name",
    "hardenedRuntime": true
  }
}
```

## 🚀 Distribution

### Release Process

```bash
# 1. Update version
npm version patch

# 2. Build all platforms
npm run dist

# 3. Create GitHub release
gh release create v$(node -p "require('./package.json').version") \
  --title "Nova Voice v$(node -p "require('./package.json').version")" \
  --notes-file RELEASE_NOTES.md \
  dist/*

# 4. Upload to download page
# Copy files from dist/ to your download hosting
```

### Platform-Specific Distribution

#### Windows
- **NSIS Installer**: `NovaVoice-Setup-1.0.0.exe` (recommended)
- **Portable**: `NovaVoice-1.0.0.exe` (no installation required)
- **Microsoft Store**: Submit `.appx` package

#### macOS
- **DMG**: `NovaVoice-1.0.0.dmg` (drag to Applications)
- **ZIP**: `NovaVoice-1.0.0-mac.zip` (manual install)
- **Mac App Store**: Submit through App Store Connect

#### Linux
- **AppImage**: `NovaVoice-1.0.0.AppImage` (universal Linux binary)
- **DEB**: `novavoice_1.0.0_amd64.deb` (Debian/Ubuntu)
- **RPM**: `novavoice-1.0.0.x86_64.rpm` (Red Hat/Fedora)

## 📊 Build Optimization

### Bundle Size Analysis

```bash
# Install bundle analyzer
npm install --save-dev @next/bundle-analyzer

# Analyze bundle
npm run build:analyze

# View report in browser
# Look for large dependencies to optimize
```

### Common Optimizations

```javascript
// next.config.mjs - bundle optimizations
const nextConfig = {
  // Remove unused dependencies
  experimental: {
    optimizePackageImports: ['lucide-react']
  },

  // Lazy load heavy components
  webpack: (config) => {
    config.externals = config.externals || []
    config.externals.push({
      'robotjs': 'commonjs robotjs'  // Don't bundle robotjs in renderer
    })
    return config
  }
}
```

### Tree Shaking

```javascript
// Optimize imports to enable tree shaking
import { Button } from '@/components/ui/button'        // ✅ Tree shakeable
import * as Icons from 'lucide-react'                  // ❌ Not tree shakeable
import { Mic } from 'lucide-react'                     // ✅ Tree shakeable
```

### Asset Optimization

```javascript
// next.config.mjs - image optimization
const nextConfig = {
  images: {
    formats: ['image/webp', 'image/avif'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384]
  }
}
```

## 🔄 Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/build.yml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ${{ matrix.os }}

    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build Next.js
        run: npm run build

      - name: Build Electron
        run: npm run electron:dist
        env:
          WIN_CERT_PASSWORD: ${{ secrets.WIN_CERT_PASSWORD }}
          APPLE_ID: ${{ secrets.APPLE_ID }}
          APPLE_APP_SPECIFIC_PASSWORD: ${{ secrets.APPLE_APP_SPECIFIC_PASSWORD }}

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: nova-voice-${{ matrix.os }}
          path: dist/
```

### Build Caching

```yaml
# Cache node_modules and Next.js cache
- name: Cache dependencies
  uses: actions/cache@v3
  with:
    path: |
      ~/.npm
      .next/cache
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

## 🧪 Testing Builds

### Pre-release Testing

```bash
# Test build locally before releasing
npm run build
npm run electron

# Test packaged application
npm run electron:pack
# Test the unpacked app in dist/mac-arm64/NovaVoice.app (or equivalent)

# Test installer
npm run electron:dist
# Install and test the generated installer
```

### Automated Testing

```yaml
# .github/workflows/test.yml
name: Test Build

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: npm test

      - name: Build Next.js
        run: npm run build

      - name: Test Electron build
        run: npm run electron:pack
```

## 🚨 Troubleshooting Builds

### Common Build Issues

#### Next.js Build Failures

**Issue**: "Build failed because of webpack errors"
```
Solutions:
- Clear Next.js cache: rm -rf .next
- Check for TypeScript errors: npm run type-check
- Update dependencies: npm update
- Check node_modules: rm -rf node_modules && npm install
```

**Issue**: "Static export failed"
```
Solutions:
- Ensure all pages use 'use client' directive
- Check for server-side code in components
- Verify all images are handled properly
- Use dynamic imports for client-only code
```

#### Electron Build Failures

**Issue**: "Cannot find module" during packaging
```
Solutions:
- Add missing files to electron-builder.json "files" array
- Check that all dependencies are in package.json
- Ensure build scripts complete successfully
- Check for native module compatibility
```

**Issue**: Code signing fails
```
Solutions:
- Verify certificate is valid and not expired
- Check certificate password and file path
- Ensure timestamp server is accessible
- Try different code signing service
```

#### Platform-Specific Issues

**Windows**: Missing Visual C++ Redistributables
```bash
# Include in installer
"nsis": {
  "include": "build/installer.nsh"
}
```

**macOS**: Code signing issues
```bash
# Check certificate
security find-identity -v
# Verify app signature
codesign -dv dist/mac/NovaVoice.app
```

**Linux**: Missing dependencies
```bash
# Test AppImage on clean system
docker run --rm -v $(pwd)/dist:/app ubuntu:20.04 /app/NovaVoice.AppImage --appimage-extract-and-run
```

### Performance Issues

#### Large Bundle Size
```bash
# Analyze bundle
npm install -g webpack-bundle-analyzer
npx webpack-bundle-analyzer out/static/chunks/*.js

# Common fixes:
# 1. Lazy load heavy components
# 2. Remove unused dependencies
# 3. Use dynamic imports
# 4. Optimize images
```

#### Slow Builds
```bash
# Use build cache
npm run build --cache

# Parallel processing
export NODE_OPTIONS="--max-old-space-size=4096"

# Disable source maps in production
const nextConfig = {
  productionBrowserSourceMaps: false
}
```

## 📋 Build Checklist

### Pre-Build
- [ ] All tests passing
- [ ] Dependencies updated
- [ ] Version number updated
- [ ] Changelog updated
- [ ] Code signed (production)

### Build Process
- [ ] Next.js build successful
- [ ] Electron packaging successful
- [ ] All target platforms built
- [ ] Installers created and tested
- [ ] File sizes reasonable

### Post-Build
- [ ] Installers tested on clean machines
- [ ] Auto-updater tested
- [ ] Release notes written
- [ ] Download links updated
- [ ] Users notified of update

---

**The build system is designed to create optimized, distributable applications for multiple platforms with comprehensive testing and deployment automation.**
