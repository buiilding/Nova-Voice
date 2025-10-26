# Live Subtitles Guide

Complete guide to the live subtitle functionality - real-time on-screen transcription and translation overlay.

## 🎭 Overview

Live subtitles provide real-time, on-screen display of speech-to-text transcription and translation. Unlike voice typing (which inputs text into applications), live subtitles create a transparent overlay window that displays transcribed text above all other windows.

## ✨ Key Features

- **Real-time Display**: Instant transcription and translation overlay
- **Dual Language**: Shows both original transcription and translated text
- **Transparent Overlay**: Glassmorphism design that's always visible
- **Click-through**: Doesn't interfere with underlying application interaction
- **Positioning**: Bottom-aligned, full-screen width display
- **Auto-sizing**: Text crops to fit overlay width (last 85 characters)

## 🚀 How It Works

### Technical Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Speech Input  │────│   Backend STT   │────│ Transcription   │
│   (Microphone)  │    │   + Translation │    │   Results       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Main Process  │────│     IPC        │────│ Subtitle Window │
│   (Electron)    │    │   Messages     │    │   (Overlay)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Window Management

The subtitle system creates a separate Electron window with special properties:

```javascript
// Main process - subtitle window creation
const subtitleWindow = new BrowserWindow({
  width: screenWidth,           // Full screen width
  height: 140,                  // Fixed height overlay
  x: 0,                        // Left edge of screen
  y: screenHeight - 140,       // Bottom of screen
  frame: false,                // No window frame
  transparent: true,           // Transparent background
  alwaysOnTop: true,           // Stays above all windows
  skipTaskbar: true,           // Hidden from taskbar
  focusable: false,            // Click-through enabled
  show: false                  // Initially hidden
})
```

### Visual Design

- **Glassmorphism**: Semi-transparent background with backdrop blur
- **Dual Bubbles**: Separate containers for transcription and translation
- **Typography**: Clear, readable fonts optimized for overlay display
- **Color Coding**: Different colors for original vs translated text

## 🎮 Usage

### Activating Live Subtitles

1. **Start the Application**: Launch Nova Voice
2. **Switch to Subtitle Mode**: Click the "Live Subtitle" button or press `Win+Alt+L`
3. **Begin Speaking**: Start speaking into your microphone
4. **View Overlay**: Transcription appears in the bottom overlay

### Keyboard Shortcuts

- **`Win+Alt+L`**: Toggle live subtitle mode on/off
- **`Win+Alt+V`**: Switch to voice typing mode
- **`Win+Alt+H`**: Hide the main application window

### Visual Indicators

- **Blue Button**: Live subtitle mode active
- **Green Indicator**: Active recording and transcription
- **Overlay Window**: Semi-transparent bar at screen bottom

## 🔧 Configuration

### Subtitle Display Settings

```typescript
// Subtitle window configuration
const SUBTITLE_CONFIG = {
  height: 140,                    // Overlay height in pixels
  maxTextLength: 85,             // Maximum characters displayed
  fontSize: {
    transcription: '16px',
    translation: '14px'
  },
  colors: {
    transcription: '#ffffff',     // White text
    translation: '#a0a0a0',       // Gray text
    background: 'rgba(0,0,0,0.7)' // Semi-transparent black
  }
}
```

### Window Positioning

- **Default**: Bottom of screen, full width
- **Customization**: Can be modified in `electron/main.js`
- **Multi-monitor**: Positions on primary display

### Performance Settings

- **Update Frequency**: Real-time updates as transcription arrives
- **Memory Management**: Automatic cleanup of old text
- **Rendering**: Hardware-accelerated for smooth performance

## 🎨 Visual Design

### Subtitle Bubble Layout

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  [English] Hello world, how are you today?             │
│                                                         │
│  [Spanish] Hola mundo, ¿cómo estás hoy?                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Styling Details

- **Background**: Semi-transparent black with blur effect
- **Text**: High-contrast white/gray for readability
- **Spacing**: Generous padding for comfortable reading
- **Animation**: Smooth fade-in/out transitions

### Responsive Behavior

- **Text Cropping**: Automatically truncates long text to fit width
- **Font Scaling**: Adjusts based on available space
- **Multi-line**: Supports multiple lines when needed

## 🔄 Data Flow

### Message Processing

1. **Audio Capture**: Microphone input captured via Web Audio API
2. **WebSocket Transmission**: Audio sent to backend gateway
3. **Speech Recognition**: Backend processes audio with STT models
4. **Translation**: Text translated using NLLB models
5. **Result Delivery**: Transcription + translation returned via WebSocket
6. **IPC Forwarding**: Main process forwards to subtitle window
7. **DOM Update**: Subtitle window updates text content
8. **Visual Display**: Text appears in overlay bubbles

### Timing Considerations

- **Real-time Updates**: Text appears as soon as backend processes it
- **Buffering**: Small delay to ensure complete utterances
- **Smoothing**: Prevents jarring text updates with pacing controls

## 🐛 Troubleshooting

### Common Issues

#### "Subtitle window doesn't appear"
```
Possible causes:
- Mode not activated (check if Live Subtitle button is blue)
- Backend not running (verify gateway connection)
- Window creation failed (check Electron console logs)
```

#### "Text is cut off or truncated"
```
Solutions:
- Check maxTextLength setting (default: 85 characters)
- Verify window width matches screen resolution
- Adjust font size if needed
```

#### "Overlay appears behind other windows"
```
Fix: Ensure alwaysOnTop: true in window configuration
Check: Other applications might override window z-order
```

#### "Text appears but is garbled/unreadable"
```
Check: Font rendering issues
Verify: CSS backdrop-filter support
Test: Different screen resolutions
```

#### "High CPU usage with subtitles active"
```
Optimize: Reduce update frequency
Check: Hardware acceleration enabled
Monitor: GPU utilization
```

### Debug Commands

```bash
# Enable subtitle debug logging
DEBUG=subtitles npm run electron

# Check window creation logs
# Look for "Subtitle window created successfully"

# Verify IPC communication
# Check for "updateDualText called" messages

# Test manual subtitle update
# Use Electron DevTools console to call subtitle functions
```

### Performance Monitoring

```javascript
// Monitor subtitle window performance
const subtitleWindow = // get subtitle window reference

// Check memory usage
const memInfo = subtitleWindow.webContents.getProcessMemoryInfo()
console.log('Subtitle window memory:', memInfo)

// Monitor frame rate
subtitleWindow.webContents.executeJavaScript(`
  // Inject performance monitoring
  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      console.log('Subtitle render time:', entry.duration)
    }
  })
  observer.observe({ entryTypes: ['measure'] })
`)
```

## 🎯 Best Practices

### For Users

- **Position Awareness**: Know where the overlay appears on screen
- **Application Compatibility**: Test with applications you'll be using
- **Audio Quality**: Use good microphone for best transcription
- **Language Selection**: Choose appropriate source/target languages

### For Developers

- **Window Management**: Handle multi-monitor setups properly
- **Performance**: Optimize rendering for smooth text updates
- **Accessibility**: Consider screen reader compatibility
- **Cross-platform**: Test on different operating systems

### For Content Creators

- **Presentation Mode**: Use for live presentations with audience translation
- **Recording**: Great for recording sessions with real-time subtitles
- **Accessibility**: Helps hearing-impaired participants
- **Multi-language**: Supports diverse audiences

## 🔧 Advanced Configuration

### Custom Styling

```css
/* Custom subtitle styles in subtitle window */
.subtitle-overlay {
  backdrop-filter: blur(10px);
  background: rgba(0, 0, 0, 0.8);
}

.subtitle-bubble {
  font-family: 'Inter', sans-serif;
  line-height: 1.4;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
}

.transcription-text {
  color: #ffffff;
  font-weight: 500;
}

.translation-text {
  color: #cccccc;
  font-weight: 400;
}
```

### Window Customization

```javascript
// Advanced window configuration
const customSubtitleConfig = {
  // Positioning
  position: 'bottom',      // 'top', 'bottom', 'custom'
  offset: 0,              // Pixels from edge
  width: '100%',          // Full width or percentage

  // Appearance
  opacity: 0.8,           // Background opacity
  blur: 10,               // Backdrop blur intensity

  // Behavior
  autoHide: false,        // Hide when no text
  fadeTime: 300,          // Fade in/out duration

  // Text settings
  maxLines: 2,            // Maximum text lines
  wordWrap: true,         // Wrap long text
  alignment: 'center'     // 'left', 'center', 'right'
}
```

## 🚀 Future Enhancements

### Planned Features

- **Customizable Positioning**: Drag to reposition overlay
- **Multiple Overlay Sizes**: Small, medium, large options
- **Theme Support**: Light/dark/custom color schemes
- **Font Customization**: Choose from different fonts
- **Size Adjustment**: Dynamic height based on content
- **Multi-language Display**: Show multiple translations simultaneously

### Technical Improvements

- **Better Performance**: Reduce CPU usage with optimized rendering
- **Enhanced Accessibility**: Screen reader support
- **Mobile Support**: Responsive design for different screen sizes
- **Animation Effects**: Smooth text transitions and effects

## 📚 Related Documentation

- **[ARCHITECTURE_OVERVIEW.md](ARCHITECTURE_OVERVIEW.md)** - Technical implementation details
- **[AUDIO_MANAGEMENT.md](AUDIO_MANAGEMENT.md)** - Audio input and processing
- **[WEBSOCKET_CLIENT.md](WEBSOCKET_CLIENT.md)** - Real-time data communication
- **[DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md)** - Development and testing

---

**Live subtitles provide an accessible, real-time way to display speech-to-text transcription and translation, making content more inclusive and enabling seamless multilingual communication.**
