# Audio Management Guide

Comprehensive guide to audio capture, processing, and device management in the Nova Voice frontend application.

## 🎵 Audio Architecture Overview

The frontend handles audio capture from microphones and system output, processes it in real-time, and streams it to the backend for transcription.

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Audio Input   │────│   Audio Proc.   │────│   WebSocket     │
│   (Devices)     │    │   (Recording)   │    │   Stream        │
│                 │    │                 │    │                 │
│ • Microphone    │    │ • Resampling    │    │ • Binary Data   │
│ • System Audio  │    │ • Normalization │    │ • Real-time     │
│ • Device Mgmt   │    │ • Level Monitor │    │ • Compression   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🎤 Audio Device Management

### Device Enumeration

The application discovers and categorizes audio devices using the MediaDevices API.

```typescript
// lib/audio-devices.ts
export class AudioDeviceManager {
  private devices: MediaDeviceInfo[] = []

  async enumerateDevices(): Promise<AudioDeviceInfo[]> {
    try {
      // Request microphone permission implicitly
      await navigator.mediaDevices.getUserMedia({ audio: true })

      // Get all media devices
      const devices = await navigator.mediaDevices.enumerateDevices()

      // Filter and categorize audio devices
      this.devices = devices.filter(device =>
        device.kind === 'audioinput' || device.kind === 'audiooutput'
      )

      return this.categorizeDevices(this.devices)
    } catch (error) {
      console.error('Failed to enumerate audio devices:', error)
      throw new Error('Microphone permission denied or devices unavailable')
    }
  }

  private categorizeDevices(devices: MediaDeviceInfo[]): AudioDeviceInfo[] {
    return devices.map(device => ({
      ...device,
      category: this.categorizeDevice(device),
      isDefault: this.isDefaultDevice(device)
    }))
  }

  private categorizeDevice(device: MediaDeviceInfo): DeviceCategory {
    const label = device.label.toLowerCase()

    // Special handling for system audio
    if (label.includes('stereo mix') ||
        label.includes('what u hear') ||
        label.includes('soundflower') ||
        label.includes('soundflowerbed')) {
      return 'system-audio'
    }

    // Categorize input devices
    if (device.kind === 'audioinput') {
      if (label.includes('microphone') || label.includes('mic')) {
        return 'microphone'
      }
      if (label.includes('headset') || label.includes('headphone')) {
        return 'headset'
      }
      if (label.includes('webcam') || label.includes('camera')) {
        return 'webcam'
      }
      return 'microphone' // Default fallback
    }

    // Categorize output devices
    if (device.kind === 'audiooutput') {
      if (label.includes('headphone') || label.includes('headset')) {
        return 'headphones'
      }
      if (label.includes('speaker') || label.includes('speakers')) {
        return 'speakers'
      }
      return 'speakers' // Default fallback
    }

    return 'unknown'
  }

  private isDefaultDevice(device: MediaDeviceInfo): boolean {
    // Check if this is the default device
    // Note: Default device info is limited due to browser security
    return device.deviceId === 'default'
  }

  getDevicesByCategory(category: DeviceCategory): MediaDeviceInfo[] {
    return this.devices.filter(device =>
      this.categorizeDevice(device) === category
    )
  }

  getPreferredDevice(category: DeviceCategory): MediaDeviceInfo | null {
    const categoryDevices = this.getDevicesByCategory(category)

    // Prefer default device if available
    const defaultDevice = categoryDevices.find(device => device.deviceId === 'default')
    if (defaultDevice) return defaultDevice

    // Otherwise return first available device
    return categoryDevices[0] || null
  }
}
```

### Device Selection UI

```typescript
// components/AudioDeviceSelector.tsx
export function AudioDeviceSelector({
  value,
  onValueChange,
  placeholder = "Select audio device",
  className = "",
  onOpenChange
}: AudioDeviceSelectorProps) {

  const [devices, setDevices] = useState<AudioDeviceInfo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDevices()
  }, [])

  const loadDevices = async () => {
    try {
      setIsLoading(true)
      const deviceManager = new AudioDeviceManager()
      const allDevices = await deviceManager.enumerateDevices()
      setDevices(allDevices)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load devices')
      setDevices([])
    } finally {
      setIsLoading(false)
    }
  }

  const getSelectedDeviceLabel = () => {
    if (!value) return placeholder
    const device = devices.find(d => d.deviceId === value)
    return device ? device.label : placeholder
  }

  const categorizedDevices = useMemo(() => {
    const categories: Record<string, MediaDeviceInfo[]> = {}

    devices.forEach(device => {
      const category = device.category || 'other'
      if (!categories[category]) {
        categories[category] = []
      }
      categories[category].push(device)
    })

    return categories
  }, [devices])

  return (
    <Select value={value} onValueChange={onValueChange} onOpenChange={onOpenChange}>
      <SelectTrigger className={cn("w-full h-10 bg-slate-800/50 border border-slate-600 text-white", className)}>
        <SelectValue placeholder={isLoading ? "Loading devices..." : placeholder}>
          {isLoading ? "Loading devices..." : getSelectedDeviceLabel()}
        </SelectValue>
      </SelectTrigger>

      <SelectContent className="bg-slate-800 border border-slate-600 max-h-80">
        {error ? (
          <div className="p-4 text-center text-red-400">
            <p className="text-sm">{error}</p>
            <button
              onClick={loadDevices}
              className="mt-2 text-xs text-blue-400 hover:text-blue-300"
            >
              Retry
            </button>
          </div>
        ) : isLoading ? (
          <div className="p-4 text-center text-slate-400">
            Loading audio devices...
          </div>
        ) : (
          Object.entries(categorizedDevices).map(([category, categoryDevices]) => (
            <div key={category}>
              <div className="px-2 py-1 text-xs font-semibold text-slate-400 uppercase tracking-wide">
                {category.replace('-', ' ')}
              </div>
              {categoryDevices.map((device) => (
                <SelectItem
                  key={device.deviceId}
                  value={device.deviceId}
                  className="text-white hover:bg-slate-700 text-sm"
                >
                  <div className="flex items-center gap-2">
                    {device.deviceId === 'default' && (
                      <span className="text-xs text-blue-400">(Default)</span>
                    )}
                    <span className="truncate">{device.label || `Device ${device.deviceId.slice(0, 8)}`}</span>
                  </div>
                </SelectItem>
              ))}
            </div>
          ))
        )}
      </SelectContent>
    </Select>
  )
}
```

## 🎚️ Audio Recording and Processing

### Web Audio API Integration

The application uses the Web Audio API for real-time audio capture and processing.

```typescript
// lib/audio-recorder.ts
export class AudioRecorder {
  private audioContext: AudioContext | null = null
  private mediaStream: MediaStream | null = null
  private mediaRecorder: MediaRecorder | null = null
  private processor: ScriptProcessorNode | null = null
  private analyser: AnalyserNode | null = null

  private onDataAvailable?: (audioData: Float32Array, sampleRate: number) => void
  private onLevelChange?: (level: number) => void

  async initialize(deviceId?: string): Promise<void> {
    try {
      // Create audio context
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: 16000 // Optimized for speech recognition
      })

      // Get user media (microphone or system audio)
      const constraints: MediaStreamConstraints = {
        audio: deviceId ? { deviceId: { exact: deviceId } } : true
      }

      this.mediaStream = await navigator.mediaDevices.getUserMedia(constraints)

      // Create analyser for level monitoring
      const source = this.audioContext.createMediaStreamSource(this.mediaStream)
      this.analyser = this.audioContext.createAnalyser()
      this.analyser.fftSize = 256

      source.connect(this.analyser)

      // Create script processor for audio data
      this.processor = this.audioContext.createScriptProcessor(4096, 1, 1)
      this.processor.onaudioprocess = (event) => {
        this.handleAudioProcess(event)
      }

      source.connect(this.processor)
      this.processor.connect(this.audioContext.destination)

    } catch (error) {
      console.error('Failed to initialize audio recorder:', error)
      throw error
    }
  }

  private handleAudioProcess(event: AudioProcessingEvent): void {
    const inputBuffer = event.inputBuffer
    const audioData = inputBuffer.getChannelData(0) // Mono audio

    // Calculate audio level
    if (this.analyser) {
      const bufferLength = this.analyser.frequencyBinCount
      const dataArray = new Uint8Array(bufferLength)
      this.analyser.getByteFrequencyData(dataArray)

      // Calculate RMS level
      let sum = 0
      for (let i = 0; i < bufferLength; i++) {
        sum += dataArray[i] * dataArray[i]
      }
      const rms = Math.sqrt(sum / bufferLength)
      const level = rms / 128 // Normalize to 0-1

      this.onLevelChange?.(level)
    }

    // Send audio data to callback
    this.onDataAvailable?.(audioData, this.audioContext!.sampleRate)
  }

  setDataCallback(callback: (audioData: Float32Array, sampleRate: number) => void): void {
    this.onDataAvailable = callback
  }

  setLevelCallback(callback: (level: number) => void): void {
    this.onLevelChange = callback
  }

  async startRecording(): Promise<void> {
    if (!this.audioContext) {
      throw new Error('Audio recorder not initialized')
    }

    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume()
    }

    console.log('Audio recording started')
  }

  stopRecording(): void {
    if (this.processor) {
      this.processor.disconnect()
      this.processor = null
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop())
      this.mediaStream = null
    }

    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close()
      this.audioContext = null
    }

    console.log('Audio recording stopped')
  }

  isRecording(): boolean {
    return this.audioContext !== null &&
           this.audioContext.state === 'running' &&
           this.mediaStream !== null
  }

  getCurrentLevel(): number {
    if (!this.analyser) return 0

    const bufferLength = this.analyser.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)
    this.analyser.getByteFrequencyData(dataArray)

    let sum = 0
    for (let i = 0; i < bufferLength; i++) {
      sum += dataArray[i] * dataArray[i]
    }
    const rms = Math.sqrt(sum / bufferLength)

    return rms / 128 // Normalize to 0-1
  }
}
```

### Audio Processing Pipeline

```typescript
// Audio data flows through this pipeline
Microphone/SysAudio → MediaStream → AudioContext → AnalyserNode → ScriptProcessor → WebSocket
      ↓                    ↓             ↓             ↓              ↓              ↓
   Raw Audio          Browser API    Frequency     Audio Data    Binary         Backend
   Samples            Stream         Analysis       Processing    Encoding      Processing
```

### System Audio Capture

Capturing system audio (desktop sound) requires special handling due to browser security restrictions.

```typescript
// For system audio capture
async function getSystemAudioStream(): Promise<MediaStream> {
  try {
    // Request screen sharing permission
    // This is the only way to access system audio in browsers
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: true, // Required for screen sharing
      audio: {
        // Request system audio loopback
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
        // Some browsers support additional constraints
        ...(navigator.userAgent.includes('Chrome') ? {
          mandatory: {
            chromeMediaSource: 'desktop',
            chromeMediaSourceId: 'system' // May not be supported
          }
        } : {})
      }
    })

    // Extract audio track only
    const audioTracks = stream.getAudioTracks()
    if (audioTracks.length === 0) {
      throw new Error('No audio track available in screen capture')
    }

    // Create new stream with only audio
    const audioStream = new MediaStream(audioTracks)

    // Stop video track (we don't need it)
    stream.getVideoTracks().forEach(track => track.stop())

    return audioStream

  } catch (error) {
    console.error('Failed to capture system audio:', error)

    if (error.name === 'NotAllowedError') {
      throw new Error('Screen sharing permission denied. Please allow screen sharing to capture system audio.')
    }

    throw new Error(`System audio capture failed: ${error.message}`)
  }
}
```

## 📊 Audio Level Monitoring

### Visual Feedback

The application provides real-time audio level visualization.

```typescript
// hooks/useAudioRecording.ts
export function useAudioRecording() {
  const [audioLevel, setAudioLevel] = useState(0)
  const recorderRef = useRef<AudioRecorder | null>(null)

  const startRecording = useCallback(async () => {
    if (!recorderRef.current) {
      recorderRef.current = new AudioRecorder()
      await recorderRef.current.initialize(selectedDevice)

      // Set up level monitoring
      recorderRef.current.setLevelCallback((level) => {
        setAudioLevel(level)
      })

      // Set up audio data callback
      recorderRef.current.setDataCallback((audioData, sampleRate) => {
        // Send to WebSocket
        window.electronAPI.sendAudioData(audioData, sampleRate)
      })
    }

    await recorderRef.current.startRecording()
  }, [selectedDevice])

  return {
    audioLevel, // 0-1 normalized level
    startRecording,
    stopRecording,
    isRecording: () => recorderRef.current?.isRecording() || false
  }
}
```

### Level Visualization Component

```typescript
// components/AudioLevelIndicator.tsx
export function AudioLevelIndicator({ level }: { level: number }) {
  // Convert level to visual bars (0-10)
  const barCount = Math.floor(level * 10)

  return (
    <div className="flex items-end gap-1 h-6">
      {Array.from({ length: 10 }, (_, i) => (
        <div
          key={i}
          className={cn(
            "w-1 bg-gradient-to-t rounded-sm transition-all duration-75",
            i < barCount
              ? level > 0.7
                ? "bg-red-400 from-red-400 to-red-600"
                : level > 0.4
                ? "bg-yellow-400 from-yellow-400 to-yellow-600"
                : "bg-green-400 from-green-400 to-green-600"
              : "bg-slate-600"
          )}
          style={{
            height: i < barCount ? `${20 + (i * 8)}%` : '20%'
          }}
        />
      ))}
    </div>
  )
}
```

## 🔧 Audio Device Permissions

### Permission Handling

```typescript
// Check and request microphone permissions
async function checkMicrophonePermission(): Promise<PermissionState> {
  try {
    // Check current permission state
    if ('permissions' in navigator) {
      const permission = await navigator.permissions.query({ name: 'microphone' })
      return permission.state
    }

    // Fallback: try to get user media
    await navigator.mediaDevices.getUserMedia({ audio: true })
    return 'granted'
  } catch (error) {
    if (error.name === 'NotAllowedError') {
      return 'denied'
    }
    if (error.name === 'NotFoundError') {
      return 'not-found'
    }
    throw error
  }
}

// Request microphone access
async function requestMicrophoneAccess(): Promise<MediaStream> {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: false,    // Disable for better audio quality
        noiseSuppression: false,    // Keep original audio
        autoGainControl: true,      // Normalize levels
        sampleRate: 16000,          // Optimize for speech
        channelCount: 1             // Mono audio
      }
    })

    return stream
  } catch (error) {
    console.error('Microphone access failed:', error)

    // Provide user-friendly error messages
    switch (error.name) {
      case 'NotAllowedError':
        throw new Error('Microphone access denied. Please allow microphone access in your browser settings.')
      case 'NotFoundError':
        throw new Error('No microphone found. Please connect a microphone and try again.')
      case 'NotReadableError':
        throw new Error('Microphone is already in use by another application.')
      default:
        throw new Error(`Microphone access failed: ${error.message}`)
    }
  }
}
```

### System Audio Permissions

```typescript
// Request screen sharing for system audio
async function requestSystemAudioAccess(): Promise<MediaStream> {
  try {
    // Show user-friendly prompt
    const stream = await navigator.mediaDevices.getDisplayMedia({
      video: {
        displaySurface: 'monitor',
        // Don't constrain video since we only want audio
      },
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
        // Some browsers support system audio
        ...(navigator.userAgent.includes('Chrome') ? {
          mandatory: {
            chromeMediaSource: 'desktop'
          }
        } : {})
      }
    })

    return stream
  } catch (error) {
    console.error('System audio access failed:', error)

    if (error.name === 'NotAllowedError') {
      throw new Error(
        'Screen sharing permission denied. To capture system audio, you need to allow screen sharing. ' +
        'Select "Share entire screen" or the application whose audio you want to capture.'
      )
    }

    if (error.name === 'NotFoundError') {
      throw new Error('No screen sharing capability found.')
    }

    throw new Error(`System audio access failed: ${error.message}`)
  }
}
```

## 🎛️ Audio Configuration

### Browser Audio Constraints

```typescript
// Optimal audio constraints for speech recognition
const AUDIO_CONSTRAINTS: MediaTrackConstraints = {
  // Disable audio processing for better quality
  echoCancellation: false,
  noiseSuppression: false,
  autoGainControl: true,

  // Optimize for speech
  sampleRate: { ideal: 16000 },
  channelCount: { ideal: 1, max: 1 },

  // Device selection
  deviceId: selectedDeviceId ? { exact: selectedDeviceId } : undefined,

  // Advanced constraints (browser-dependent)
  latency: { ideal: 0.01 },           // 10ms latency
  sampleSize: { ideal: 16 },          // 16-bit samples
  volume: { ideal: 1.0, max: 1.0 }   // Full volume
}
```

### Audio Processing Parameters

```typescript
// Audio processing configuration
const AUDIO_CONFIG = {
  // Web Audio API settings
  sampleRate: 16000,
  channelCount: 1,
  bitDepth: 16,

  // Processing buffer
  bufferSize: 4096,        // ScriptProcessorNode buffer
  fftSize: 256,           // AnalyserNode FFT size

  // Level monitoring
  smoothingTimeConstant: 0.8,
  minDecibels: -90,
  maxDecibels: -10,

  // Quality thresholds
  silenceThreshold: 0.01,  // Minimum level to consider "speaking"
  clippingThreshold: 0.95, // Maximum level before clipping

  // Transmission
  compression: 'none',     // No compression for now
  encoding: 'linear',      // Linear PCM
  endianness: 'little'     // Little-endian byte order
}
```

## 🐛 Troubleshooting Audio Issues

### Common Problems and Solutions

#### "Microphone permission denied"
```
Symptoms: getUserMedia() throws NotAllowedError
Solutions:
1. Check browser settings for microphone permissions
2. Ensure HTTPS (required for microphone access)
3. Try refreshing the page and granting permission again
4. Check if microphone is being used by another application
```

#### "No audio devices found"
```
Symptoms: enumerateDevices() returns empty array
Solutions:
1. Check if microphone is physically connected
2. Verify microphone drivers are installed (Windows)
3. Try unplugging and replugging the microphone
4. Check system sound settings
5. Try a different USB port
```

#### "Audio is too quiet/loud"
```
Symptoms: Audio level monitoring shows incorrect levels
Solutions:
1. Check autoGainControl setting in constraints
2. Adjust microphone volume in system settings
3. Move closer/further from microphone
4. Check for background noise interference
```

#### "System audio not working"
```
Symptoms: getDisplayMedia() fails or no audio in stream
Solutions:
1. Select "Share entire screen" instead of specific window
2. Ensure application audio is not muted
3. Check system audio settings
4. Try different browser (Chrome works best)
5. Some applications don't output to system audio
```

#### "Audio is choppy/distorted"
```
Symptoms: Audio playback has gaps or distortion
Solutions:
1. Reduce bufferSize in ScriptProcessorNode
2. Check CPU usage (close other applications)
3. Lower sampleRate if device can't handle 16kHz
4. Check for browser tab throttling
5. Ensure stable network connection for WebSocket
```

#### "Echo or feedback"
```
Symptoms: Hearing own voice through speakers
Solutions:
1. Use headphones instead of speakers
2. Enable echoCancellation in constraints
3. Lower speaker volume
4. Move microphone away from speakers
5. Check for audio loopback in system settings
```

### Debugging Audio Issues

```typescript
// Enable detailed audio logging
const DEBUG_AUDIO = process.env.DEBUG_AUDIO === 'true'

class AudioDebugger {
  static logDeviceInfo(devices: MediaDeviceInfo[]) {
    if (!DEBUG_AUDIO) return

    console.group('🎤 Audio Devices')
    devices.forEach((device, index) => {
      console.log(`${index + 1}. ${device.label}`)
      console.log(`   ID: ${device.deviceId}`)
      console.log(`   Kind: ${device.kind}`)
      console.log(`   Group: ${device.groupId}`)
    })
    console.groupEnd()
  }

  static logAudioConstraints(constraints: MediaStreamConstraints) {
    if (!DEBUG_AUDIO) return

    console.log('🎵 Audio Constraints:', constraints)
  }

  static logAudioLevels(level: number, interval = 1000) {
    if (!DEBUG_AUDIO) return

    setInterval(() => {
      console.log(`📊 Audio Level: ${(level * 100).toFixed(1)}%`)
    }, interval)
  }

  static logWebSocketAudio(size: number, sampleRate: number) {
    if (!DEBUG_AUDIO) return

    console.log(`📡 Sending ${size} bytes at ${sampleRate}Hz`)
  }
}

// Usage
AudioDebugger.logDeviceInfo(devices)
AudioDebugger.logAudioConstraints(constraints)
AudioDebugger.logAudioLevels(audioLevel)
```

### Performance Monitoring

```typescript
// Monitor audio pipeline performance
class AudioPerformanceMonitor {
  private metrics = {
    devicesEnumerated: 0,
    streamsCreated: 0,
    audioProcessed: 0,
    websocketErrors: 0,
    avgProcessingTime: 0
  }

  trackDeviceEnumeration(count: number) {
    this.metrics.devicesEnumerated = count
    console.log(`📊 Devices enumerated: ${count}`)
  }

  trackStreamCreation() {
    this.metrics.streamsCreated++
    console.log(`📊 Streams created: ${this.metrics.streamsCreated}`)
  }

  trackAudioProcessing(bytes: number, timeMs: number) {
    this.metrics.audioProcessed += bytes
    this.metrics.avgProcessingTime = (this.metrics.avgProcessingTime + timeMs) / 2

    console.log(`📊 Audio processed: ${bytes} bytes in ${timeMs}ms`)
  }

  getMetrics() {
    return {
      ...this.metrics,
      totalAudioProcessed: `${(this.metrics.audioProcessed / 1024 / 1024).toFixed(2)}MB`
    }
  }
}
```

## 📚 Related Documentation

- **[DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md)** - Development workflow
- **[WEBSOCKET_CLIENT.md](WEBSOCKET_CLIENT.md)** - Audio streaming over WebSocket
- **[COMPONENT_ARCHITECTURE.md](COMPONENT_ARCHITECTURE.md)** - Audio device selector component
- **[VOICE_TYPING_ENGINE.md](VOICE_TYPING_ENGINE.md)** - How audio transcription is used

---

**Audio management is critical for the real-time nature of the application, requiring careful handling of device permissions, browser APIs, and audio processing pipelines.**
