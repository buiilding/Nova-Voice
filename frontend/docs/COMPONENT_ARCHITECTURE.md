# Component Architecture Guide

Comprehensive guide to the React component architecture, custom hooks, and patterns used in the Nova Voice frontend application.

## 🏗️ Architecture Overview

The frontend follows a modern React architecture with custom hooks for state management, modular components, and clean separation of concerns.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   App (page.tsx)│────│   Custom Hooks  │────│   Components    │
│                 │    │                 │    │                 │
│ • State orchestration│ • useConnection │ • ModeButtons      │
│ • Component composition│ • useAudioRecording│ • LangSelectors   │
│ • Layout management │ • useWindowSizing │ • StatusIndicator │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │
        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐
│   Services      │    │   UI Library    │
│                 │    │                 │
│ • Gateway API   │    │ • shadcn/ui     │
│ • Audio devices │    │ • Tailwind CSS  │
│ • Config        │    │ • Lucide icons  │
└─────────────────┘    └─────────────────┘
```

## 🎯 Core Principles

### 1. Hook-Based State Management
- **Custom hooks** encapsulate complex state logic
- **Separation of concerns** between UI and business logic
- **Reusable logic** across components
- **Testable units** for state management

### 2. Component Composition
- **Small, focused components** with single responsibilities
- **Props-driven** interfaces for flexibility
- **Composition over inheritance** patterns
- **TypeScript** for type safety

### 3. Service Layer Abstraction
- **Thin service wrappers** around external APIs
- **Consistent error handling** across services
- **Environment-based configuration**
- **Easy mocking** for testing

## 🔧 Custom Hooks Architecture

### `useConnection` - Gateway Connection Management

**Purpose**: Manages WebSocket connection to backend gateway service.

**Location**: `hooks/useConnection.ts`

**Features**:
- Connection state tracking (`connected`, `connecting`)
- Mode switching (`typing` | `subtitle`)
- Automatic reconnection logic
- Error handling and status reporting

**API**:
```typescript
const { connected, connecting, mode, connect, disconnect, setMode } = useConnection()
```

**Usage**:
```typescript
// Connect to gateway
await connect()

// Switch modes
await setMode('typing')  // or 'subtitle'

// Check status
if (connected && mode === 'typing') {
  // Enable voice typing features
}
```

**State Management**:
```typescript
interface ConnectionState {
  connected: boolean
  connecting: boolean
  mode: 'typing' | 'subtitle'
}
```

### `useAudioRecording` - Audio Processing

**Purpose**: Wraps audio recording functionality with device management.

**Location**: `hooks/useAudioRecording.ts`

**Features**:
- Audio level monitoring
- Device selection and switching
- Recording state management
- Real-time audio data processing

**API**:
```typescript
const {
  isRecording,
  audioLevel,
  selectedDevice,
  setSelectedDevice,
  startRecording,
  stopRecording
} = useAudioRecording()
```

**Usage**:
```typescript
// Start recording
await startRecording()

// Monitor audio levels
console.log('Audio level:', audioLevel)

// Change device
setSelectedDevice('device-id')
```

### `useShortcuts` - Global Keyboard Shortcuts

**Purpose**: Handles global keyboard shortcuts from Electron.

**Location**: `hooks/useShortcuts.ts`

**Features**:
- Shortcut registration and handling
- Action dispatching to components
- Electron IPC integration
- Cross-platform shortcut support

**API**:
```typescript
// Hook sets up listeners automatically
// Actions are dispatched via callback props
```

**Integration**:
```typescript
// In component that needs shortcuts
function handleVoiceTyping() {
  // Toggle voice typing mode
}

function handleLiveSubtitles() {
  // Toggle live subtitles mode
}

// Hook listens for IPC messages and calls appropriate handlers
```

### `useWindowSizing` - Dynamic Window Management

**Purpose**: Manages dynamic Electron window resizing based on UI state.

**Location**: `hooks/useWindowSizing.ts`

**Features**:
- ResizeObserver integration
- Dropdown height calculations
- Smooth window transitions
- Panel state management

**API**:
```typescript
const {
  rootRef,
  toolbarRef,
  settingsRef,
  showSettings,
  toggleSettings
} = useWindowSizing(openDropdown, pendingDropdown)
```

**Usage**:
```typescript
// Attach refs to DOM elements
<div ref={rootRef}>
  <div ref={toolbarRef}>
    {/* Toolbar content */}
  </div>
  {showSettings && (
    <div ref={settingsRef}>
      {/* Settings panel */}
    </div>
  )}
</div>
```

## 🧩 Component Patterns

### Control Panel Components

#### `ModeButtons` - Mode Toggle Buttons

**Location**: `components/control/ModeButtons.tsx`

**Purpose**: Voice typing and live subtitle mode toggles.

**Props**:
```typescript
interface ModeButtonsProps {
  voiceTypingActive: boolean
  liveSubtitleActive: boolean
  onToggleVoiceTyping: () => void
  onToggleLiveSubtitle: () => void
}
```

**Features**:
- Visual state indicators
- Keyboard shortcut hints
- Disabled states during transitions

#### `LangSelectors` - Language Dropdowns

**Location**: `components/control/LangSelectors.tsx`

**Purpose**: Source and target language selection.

**Props**:
```typescript
interface LangSelectorsProps {
  sourceLanguage: string
  targetLanguage: string
  onSourceLanguageChange: (lang: string) => void
  onTargetLanguageChange: (lang: string) => void
  openDropdown: 'source' | 'target' | 'audio' | null
  setOpenDropdown: (dropdown: 'source' | 'target' | 'audio' | null) => void
  setPendingDropdown: (dropdown: 'source' | 'target' | 'audio' | null) => void
}
```

**Features**:
- Controlled dropdown state
- Dynamic window resizing
- Language validation

#### `AudioSource` - Audio Device Selector

**Location**: `components/control/AudioSource.tsx`

**Purpose**: Audio input device selection.

**Props**:
```typescript
interface AudioSourceProps {
  selectedAudioDevice: string
  onAudioDeviceChange: (device: string) => void
  openDropdown: 'source' | 'target' | 'audio' | null
  setOpenDropdown: (dropdown: 'source' | 'target' | 'audio' | null) => void
  setPendingDropdown: (dropdown: 'source' | 'target' | 'audio' | null) => void
}
```

**Features**:
- Device enumeration integration
- System audio capture support
- Permission handling

#### `StatusIndicator` - Connection Status

**Location**: `components/control/StatusIndicator.tsx`

**Purpose**: Real-time connection and recording status display.

**Props**:
```typescript
interface StatusIndicatorProps {
  running: boolean
  connected: boolean
  listening: boolean
}
```

**States**:
- **Inactive**: Not connected, not recording
- **Connected**: Connected to gateway, not recording
- **Listening**: Connected and actively recording

### Settings Components

#### `SettingsPanel` - Configuration Panel

**Location**: `components/settings/SettingsPanel.tsx`

**Purpose**: Keybind configuration and device settings.

**Features**:
- Audio device selection
- Keyboard shortcut inputs
- Settings persistence

### UI Components

#### shadcn/ui Integration

**Location**: `components/ui/`

**Components Used**:
- `Button` - Consistent button styling
- `Select` - Dropdown components
- Custom styling with Tailwind CSS

## 📊 State Management Patterns

### Hook Composition Pattern

Components compose multiple hooks for complex functionality:

```typescript
function VoiceTranscriberApp() {
  // Connection management
  const { connected, connecting, mode, connect, disconnect, setMode } = useConnection()

  // Audio processing
  const {
    isRecording,
    audioLevel,
    selectedDevice,
    setSelectedDevice,
    startRecording,
    stopRecording
  } = useAudioRecording()

  // Window management
  const {
    rootRef,
    toolbarRef,
    settingsRef,
    showSettings,
    toggleSettings,
  } = useWindowSizing(openDropdown, pendingDropdown)

  // UI state
  const [sourceLanguage, setSourceLanguage] = useState("en")
  const [targetLanguage, setTargetLanguage] = useState("vi")

  // ... component logic
}
```

### Service Layer Pattern

Thin wrappers around external APIs:

```typescript
// lib/gateway.ts - WebSocket API wrapper
export const gateway = {
  connect: () => window.electronAPI.connectGateway(),
  disconnect: () => window.electronAPI.disconnectGateway(),
  sendAudio: (u8: Uint8Array, sr: number) => window.electronAPI.sendAudioData(u8, sr),
  setMode: (mode: 'typing'|'subtitle') => window.electronAPI.setMode(mode),
  updateLanguages: (src: string, dst: string) => window.electronAPI.updateLanguages(src, dst),
  startOver: () => window.electronAPI.sendStartOver(),
}
```

## 🔄 Data Flow Patterns

### Unidirectional Data Flow

```
User Action → Component Event → Hook Update → State Change → Re-render
      ↓
Service Call → External API → Response → State Update → UI Update
```

### WebSocket Event Handling

```
WebSocket Message → Electron IPC → Hook Listener → State Update → Component Re-render
```

### Audio Processing Pipeline

```
User Speech → Microphone → Web Audio API → Audio Recorder → Binary Encoding → WebSocket → Gateway
```

## 🧪 Testing Patterns

### Hook Testing
```typescript
// Test custom hooks in isolation
import { renderHook, act } from '@testing-library/react'
import { useConnection } from '@/hooks/useConnection'

test('connection hook works', () => {
  const { result } = renderHook(() => useConnection())

  act(() => {
    result.current.connect()
  })

  expect(result.current.connecting).toBe(true)
})
```

### Component Testing
```typescript
// Test components with mocked hooks
import { render, screen } from '@testing-library/react'
import { ModeButtons } from '@/components/control/ModeButtons'

const mockProps = {
  voiceTypingActive: false,
  liveSubtitleActive: false,
  onToggleVoiceTyping: jest.fn(),
  onToggleLiveSubtitle: jest.fn(),
}

test('mode buttons render correctly', () => {
  render(<ModeButtons {...mockProps} />)
  expect(screen.getByText('Voice Typing')).toBeInTheDocument()
})
```

## 🚀 Performance Optimization

### Hook Memoization
```typescript
// Memoize expensive computations
const processedData = useMemo(() => {
  return expensiveCalculation(data)
}, [data])
```

### Component Optimization
```typescript
// Prevent unnecessary re-renders
const MemoizedComponent = memo(function Component({ prop }) {
  return <div>{prop}</div>
})
```

### Lazy Loading
```typescript
// Load components on demand
const SettingsPanel = lazy(() => import('@/components/settings/SettingsPanel'))

function App() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <SettingsPanel />
    </Suspense>
  )
}
```

## 📋 Component Checklist

When creating new components:

- [ ] **Single Responsibility**: Does one thing well
- [ ] **TypeScript Types**: Proper type definitions
- [ ] **Props Interface**: Clear prop contracts
- [ ] **Default Props**: Sensible defaults where appropriate
- [ ] **Accessibility**: ARIA labels, keyboard navigation
- [ ] **Error Boundaries**: Graceful error handling
- [ ] **Loading States**: Handle async operations
- [ ] **Responsive Design**: Works on different screen sizes

## 🔧 Custom Hook Checklist

When creating custom hooks:

- [ ] **Clear Purpose**: Single, well-defined responsibility
- [ ] **Consistent API**: Similar patterns to existing hooks
- [ ] **TypeScript Support**: Full type safety
- [ ] **Error Handling**: Proper error states and recovery
- [ ] **Cleanup**: Proper effect cleanup
- [ ] **Testing**: Unit tests for hook logic
- [ ] **Documentation**: JSDoc comments for complex logic

## 📚 Related Documentation

- **[DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md)** - Development workflow
- **[VOICE_TYPING_ENGINE.md](VOICE_TYPING_ENGINE.md)** - Typing simulation algorithm
- **[ELECTRON_INTEGRATION.md](ELECTRON_INTEGRATION.md)** - Main/renderer processes
- **[WEBSOCKET_CLIENT.md](WEBSOCKET_CLIENT.md)** - Backend communication
- **[AUDIO_MANAGEMENT.md](AUDIO_MANAGEMENT.md)** - Audio handling

---

**The component architecture emphasizes modularity, reusability, and maintainability through custom hooks and clean component composition.**
