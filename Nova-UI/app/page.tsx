"use client"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { AudioDeviceSelector } from "@/components/audio-device-selector"
import { AudioRecorder } from "@/lib/audio-recorder"
import { audioDeviceManager } from "@/lib/audio-devices"
import {
  Mic,
  Type,
  Subtitles,
  Settings,
  LogOut,
  Eye,
  EyeOff,
  RotateCcw,
  Activity,
  Volume2,
  Headphones,
  Keyboard,
  X,
} from "lucide-react"

export default function VoiceTranscriberApp() {
  // Authentication state
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState(null)
  const [authToken, setAuthToken] = useState<string | null>(null)

  // Global token storage for Electron IPC
  const currentTokenRef = useRef<string | null>(null)

  // Check localStorage on mount and poll for auth status
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        // First check localStorage
        const storedToken = localStorage.getItem('auth_token')
        if (storedToken) {
          setAuthToken(storedToken)
          currentTokenRef.current = storedToken
          setIsAuthenticated(true)
          return
        }

        // If no localStorage token, check with backend
        const backendUrl = process.env.NODE_ENV === 'production'
          ? 'https://nova-voice.com:8080'  // Replace with your actual domain
          : 'http://localhost:8080';
        const response = await fetch(`${backendUrl}/auth/status`)
        if (response.ok) {
          const authData = await response.json()
          if (authData.authenticated && authData.token) {
            setAuthToken(authData.token)
            currentTokenRef.current = authData.token
            localStorage.setItem('auth_token', authData.token)
            setUser(authData.user)
            setIsAuthenticated(true)
          }
        }
      } catch (error) {
        console.log('Auth status check failed:', error)
      }
    }

    // Check immediately on mount
    checkAuthStatus()

    // Also check periodically in case auth completes while app is running
    const interval = setInterval(checkAuthStatus, 2000)
    return () => clearInterval(interval)
  }, [])

  const [sourceLanguage, setSourceLanguage] = useState("en")
  const [targetLanguage, setTargetLanguage] = useState("vi")
  const [isRecording, setIsRecording] = useState(false)
  const [isVisible, setIsVisible] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [waveformAnimation, setWaveformAnimation] = useState(0)
  const [voiceTypingActive, setVoiceTypingActive] = useState(false)
  const [liveSubtitleActive, setLiveSubtitleActive] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showSettingsPadding, setShowSettingsPadding] = useState(false)
  const [selectedAudioDevice, setSelectedAudioDevice] = useState<string>("")
  const [voiceTypingKeybind, setVoiceTypingKeybind] = useState("Win+Alt+V")
  const [liveSubtitleKeybind, setLiveSubtitleKeybind] = useState("Win+Alt+L")
  const [hideKeybind, setHideKeybind] = useState("Win+Alt+H")
  const [openDropdown, setOpenDropdown] = useState<'source' | 'target' | 'audio' | null>(null)
  const [pendingDropdown, setPendingDropdown] = useState<'source' | 'target' | 'audio' | null>(null)
  const [liveTranscriptionText, setLiveTranscriptionText] = useState("")
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isDisconnecting, setIsDisconnecting] = useState(false)
  
  const isConnectedRef = useRef(isConnected)
  const actionInProgress = useRef(false);
  const audioRecordingInProgress = useRef(false);
  const lastClickTime = useRef(0);
  const selectedAudioDeviceRef = useRef(selectedAudioDevice);
  const shortcutInProgress = useRef(false);
  const voiceTypingActiveRef = useRef(voiceTypingActive);
  const liveSubtitleActiveRef = useRef(liveSubtitleActive);

  useEffect(() => {
    isConnectedRef.current = isConnected
  }, [isConnected])

  useEffect(() => {
    selectedAudioDeviceRef.current = selectedAudioDevice
  }, [selectedAudioDevice])

  useEffect(() => {
    voiceTypingActiveRef.current = voiceTypingActive
  }, [voiceTypingActive])

  useEffect(() => {
    liveSubtitleActiveRef.current = liveSubtitleActive
  }, [liveSubtitleActive])

  // Audio recording state
  const [audioRecorder, setAudioRecorder] = useState<AudioRecorder | null>(null)
  const [audioLevel, setAudioLevel] = useState(0)

  // Show connection notification via separate window
  const showConnectionNotification = async (message: string) => {
    if (typeof window !== 'undefined' && (window as any).electronAPI) {
      await (window as any).electronAPI.showNotification('Connection Failed', message);
    }
  }

  // Show permission error notification via separate window
  const showPermissionErrorNotification = async (message: string) => {
    if (typeof window !== 'undefined' && (window as any).electronAPI) {
      await (window as any).electronAPI.showNotification('Audio Permission Error', message);
    }
  }
  
  // Permission and error states
  const [showPermissionDialog, setShowPermissionDialog] = useState(false)
  const [isRequestingPermission, setIsRequestingPermission] = useState(false)
  
  const rootRef = useRef<HTMLDivElement>(null)
  const toolbarRef = useRef<HTMLDivElement>(null)
  const settingsRef = useRef<HTMLDivElement>(null)
  const [panelHeights, setPanelHeights] = useState({ toolbar: 0, settings: 0 })
  const windowSizeRef = useRef({ width: 0, height: 0 })
  const animationTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Measure panel heights
  useEffect(() => {
    const elementsToObserve = [
      { ref: toolbarRef, key: 'toolbar' },
      { ref: settingsRef, key: 'settings' },
    ];

    const observers = elementsToObserve.map(({ ref, key }) => {
      if (!ref.current) return null;
      
      const observer = new ResizeObserver((entries) => {
        if (entries[0]) {
          const newHeight = Math.ceil(entries[0].target.getBoundingClientRect().height);
          setPanelHeights((prev) => 
            prev[key as keyof typeof prev] !== newHeight 
              ? { ...prev, [key]: newHeight } 
              : prev
          );
        }
      });
      
      observer.observe(ref.current);
      return observer;
    }).filter(Boolean) as ResizeObserver[];

    return () => {
      observers.forEach((observer) => observer.disconnect());
    };
  }, []);

  // Measure initial size and setup observer for width changes
  useEffect(() => {
    if (!rootRef.current) return

    const observer = new ResizeObserver((entries) => {
      if (entries[0]) {
        const newWidth = Math.ceil(entries[0].contentRect.width)

        if ((window as any).electronAPI && newWidth > 0 && newWidth !== windowSizeRef.current.width) {
          windowSizeRef.current.width = newWidth
          
          // On first measure, set initial height as well
          if (windowSizeRef.current.height === 0) {
            let initialHeight = panelHeights.toolbar
            windowSizeRef.current.height = initialHeight
          }
          
          // @ts-ignore - TypeScript conflict with other project types
          (window as any).electronAPI.setWindowSize({
            width: windowSizeRef.current.width,
            height: windowSizeRef.current.height
          });
        }
      }
    })

    observer.observe(rootRef.current)

    return () => observer.disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [panelHeights.toolbar]) // Rerun if toolbar height changes

  // Handle settings panel padding animation
  useEffect(() => {
    if (showSettings) {
      // Immediately show padding when opening
      setShowSettingsPadding(true)
    } else {
      // Delay hiding padding until after animation completes
      const timer = setTimeout(() => {
        setShowSettingsPadding(false)
      }, 500) // Match animation duration
      return () => clearTimeout(timer)
    }
  }, [showSettings])

  // Handle height changes based on UI state
  useEffect(() => {
    // Don't run until initial width and toolbar height are measured
    if (windowSizeRef.current.width === 0 || panelHeights.toolbar === 0) return

    const { toolbar, settings } = panelHeights
    const PADDING = 8 // Corresponds to pt-2/pb-2/mb-2 (0.5rem)
    const LANGUAGE_DROPDOWN_HEIGHT = 150 // Estimated height for language dropdown items
    const AUDIO_DROPDOWN_HEIGHT = 300 // More height for audio device dropdown with categories

    let targetHeight = toolbar
    if (showSettings) {
      targetHeight += PADDING * 2 // For pt-2 and pb-2 on the container
      targetHeight += settings
    }
    // Add extra height when dropdown is open or pending
    if (openDropdown || pendingDropdown) {
      // Use different heights based on dropdown type
      if (openDropdown === 'audio' || pendingDropdown === 'audio') {
        targetHeight += AUDIO_DROPDOWN_HEIGHT
      } else {
        targetHeight += LANGUAGE_DROPDOWN_HEIGHT
      }
    }

    const currentHeight = windowSizeRef.current.height
    if (targetHeight === currentHeight) return

    const isExpanding = targetHeight > currentHeight
    const width = windowSizeRef.current.width

    if (animationTimeoutRef.current) {
      clearTimeout(animationTimeoutRef.current)
    }

    const setSize = () => {
      if ((window as any).electronAPI) {
        // @ts-ignore - TypeScript conflict with other project types
        (window as any).electronAPI.setWindowSize({ width, height: targetHeight })
      }
      windowSizeRef.current.height = targetHeight
    }

    if (isExpanding) {
      // Expand: resize window first, then animate UI
      setSize()
    } else {
      // Shrink: animate UI first, then resize window
      animationTimeoutRef.current = setTimeout(setSize, 500) // Animation duration
    }
    
    return () => {
      if (animationTimeoutRef.current) {
        clearTimeout(animationTimeoutRef.current)
      }
    }
  }, [showSettings, panelHeights, openDropdown, pendingDropdown])

  // Handle pending dropdown opening after window resize
  useEffect(() => {
    if (pendingDropdown && openDropdown === null) {
      const timer = setTimeout(() => {
        setOpenDropdown(pendingDropdown)
        setPendingDropdown(null)
      }, 100) // Small delay to ensure window resize completes

      return () => clearTimeout(timer)
    }
  }, [pendingDropdown, openDropdown])

  // Update languages on gateway when they change
  useEffect(() => {
    if (typeof window !== 'undefined' && (window as any).electronAPI && isConnected) {
      (window as any).electronAPI.updateLanguages(sourceLanguage, targetLanguage);
    }
  }, [sourceLanguage, targetLanguage, isConnected])

  // Handle authentication success/error
  useEffect(() => {
    console.log('[DEBUG FRONTEND] Setting up auth event listeners...');
    console.log('[DEBUG FRONTEND] window.electronAPI available:', typeof window !== 'undefined' && (window as any).electronAPI);

    if (typeof window !== 'undefined' && (window as any).electronAPI) {
      console.log('[DEBUG FRONTEND] electronAPI found, setting up listeners');
      const electronAPI = (window as any).electronAPI;

      const handleAuthSuccess = (event: any, session: any) => {
        console.log('[DEBUG FRONTEND] Auth success received:', session);
        setIsAuthenticated(true);
        setUser(session.user);
        setAuthToken(session.token);
        currentTokenRef.current = session.token;
        localStorage.setItem('auth_token', session.token);

        // Now connect to WebSocket with auth token
        console.log('[DEBUG FRONTEND] Calling connectToBackend with token');
        connectToBackend(session.token);
      };

      const handleAuthError = (event: any, error: string) => {
        console.error('Authentication failed:', error);
        // Show error to user
        setConnectionError(error);
      };

      const handleGatewayError = (event: any, error: string) => {
        console.error('Gateway authentication failed:', error);
        setConnectionError(`Gateway authentication failed: ${error}`);
      };

      electronAPI.onAuthSuccess(handleAuthSuccess);
      electronAPI.onAuthError(handleAuthError);
      electronAPI.onGatewayError(handleGatewayError);

      console.log('[DEBUG FRONTEND] Auth event listeners registered');

      return () => {
        electronAPI.removeAllListeners('auth-success');
        electronAPI.removeAllListeners('auth-error');
        electronAPI.removeAllListeners('gateway-error');
      };
    }
  }, []);

  const connectToBackend = async (token: string) => {
    console.log('[DEBUG FRONTEND] connectToBackend called with token:', token ? 'YES' : 'NO');
    // Connect to gateway using the token for authentication
    if (typeof window !== 'undefined' && (window as any).electronAPI) {
      try {
        console.log('[DEBUG FRONTEND] Calling electronAPI.connectGateway...');
        const connectResult = await (window as any).electronAPI.connectGateway(token);
        console.log('[DEBUG FRONTEND] connectGateway result:', connectResult);
        if (connectResult.success) {
          console.log('[DEBUG FRONTEND] Connected to backend with authentication');
        } else {
          console.error('[DEBUG FRONTEND] Failed to connect to backend:', connectResult.error);
        }
      } catch (error) {
        console.error('[DEBUG FRONTEND] Failed to connect to backend:', error);
      }
    } else {
      console.error('[DEBUG FRONTEND] electronAPI not available');
    }
  };

  // Setup Electron API event listeners (no auto-connect)
  useEffect(() => {
    if (typeof window !== 'undefined' && (window as any).electronAPI) {
      const electronAPI = (window as any).electronAPI;

      // Connection status updates
      const handleConnectionStatus = (event: any, data: any) => {
        setIsConnected(data.connected);
        // Stop audio recording if disconnected
        if (!data.connected && isRecording) {
          console.log('Connection lost, stopping audio recording');
          stopAudioRecording();
        }
      };

      const handleRealtimeResult = (event: any, data: any) => {
        console.log('Received realtime result:', data);

        // Send subtitle updates for live subtitle mode
        if (liveSubtitleActive && typeof window !== 'undefined' && (window as any).electronAPI) {
          const transcriptionText = data.text || '';
          const translationText = data.translation || '';

          // Check if translation is enabled (source != target)
          const translationEnabled = sourceLanguage !== targetLanguage;

          if (translationEnabled) {
            // When translation is enabled, always send dual subtitles
            // Transcription overlay shows immediately, translation overlay shows when available
            (window as any).electronAPI.updateDualSubtitle({
              transcription: transcriptionText,
              translation: translationText
            });
          } else {
            // Translation disabled: send single subtitle
            const displayText = translationText || transcriptionText;
            (window as any).electronAPI.updateSubtitle(displayText);
          }
        }
      };

      const handleUtteranceEnd = (event: any, data: any) => {
        console.log('Utterance ended');
      };

      const handleLiveTranscriptionUpdate = (event: any, data: any) => {
        // Update the live transcription text display in the UI
        const displayText = data.translation || data.text || '';
        setLiveTranscriptionText(displayText);
      };

      // Register event listeners
      electronAPI.onConnectionStatus(handleConnectionStatus);
      electronAPI.onRealtimeResult(handleRealtimeResult);
      electronAPI.onUtteranceEnd(handleUtteranceEnd);
      electronAPI.onLiveTranscriptionUpdate(handleLiveTranscriptionUpdate);

      return () => {
        // Cleanup listeners
        electronAPI.removeAllListeners('connection-status');
        electronAPI.removeAllListeners('realtime-result');
        electronAPI.removeAllListeners('utterance-end');
        electronAPI.removeAllListeners('live-transcription-update');
      };
    }
  }, []);

  // Audio recording effects
  useEffect(() => {
    if (isRecording) {
      const interval = setInterval(() => {
        setRecordingTime((prev) => prev + 1)
        setWaveformAnimation((prev) => (prev + 1) % 360)
      }, 1000)
      setIsListening(true)
      return () => {
        clearInterval(interval)
        setIsListening(false)
      }
    } else {
      setIsListening(false)
    }
  }, [isRecording])

  // Audio recording is now handled explicitly in button handlers after successful connection
  // This useEffect is removed to prevent automatic recording on button state changes

  const startAudioRecording = async () => {
    if (!selectedAudioDeviceRef.current) {
      console.error('No audio device selected');
      return;
    }

    // Prevent multiple simultaneous recording attempts
    if (audioRecordingInProgress.current) {
      console.warn('Audio recording already in progress, ignoring request');
      return;
    }

    audioRecordingInProgress.current = true;

    try {

      // Ensure any existing recording is fully stopped
      if (audioRecorder) {
        console.log('Stopping existing audio recording before starting new one');
        await audioRecorder.stop();
        setAudioRecorder(null);
      }

      // Get the audio stream from the selected device
      // For input devices: captures from specific microphone
      // For output devices: captures system audio (ignores specific device)
      const device = await audioDeviceManager.getDeviceStream(selectedAudioDeviceRef.current);
      if (!device) {
        console.error('Selected device cannot be used for recording');
        await showPermissionErrorNotification('Selected device cannot be used for recording');
        audioRecordingInProgress.current = false;
        return;
      }

      // Log the device type being used
      const deviceInfo = audioDeviceManager.getDeviceInfo(selectedAudioDeviceRef.current);
      if (deviceInfo) {
        console.log(`Starting audio recording from ${deviceInfo.kind} device: ${deviceInfo.label}`);
      }

      const recorder = new AudioRecorder({
        deviceId: selectedAudioDeviceRef.current,
        sampleRate: 16000,
        channels: 1,
        onData: (audioData: Float32Array) => {
          // UI level meter
          const level = AudioRecorder.getAudioLevel(audioData);
          setAudioLevel(level);

          // Convert to Int16 for server transmission (little-endian PCM)
          const int16Data = AudioRecorder.float32ToInt16(audioData);

          // Send audio data to gateway via Electron backend
          if (typeof window !== 'undefined' && (window as any).electronAPI) {
            if (!isConnectedRef.current) {
              console.warn('Not connected to gateway, cannot send audio data');
              return;
            }
            const uint8Array = new Uint8Array(int16Data.buffer.slice(0));
            const sr = (recorder as any)?.getSampleRate ? (recorder as any).getSampleRate() : 16000;
            // Prefer fast, fire-and-forget channel if available
            if ((window as any).electronAPI.sendAudioChunk) {
              (window as any).electronAPI.sendAudioChunk(uint8Array, sr || 16000);
            } else {
              (window as any).electronAPI.sendAudioData(uint8Array, sr || 16000);
            }
          }
        },
        onError: async (error) => {
          console.error('Audio recording error:', error);
          setIsRecording(false);
          setAudioLevel(0);
          await showPermissionErrorNotification(error.message);
        },
        onStart: () => {
          console.log('Audio recording started');
          setIsRecording(true);
          setRecordingTime(0);
        },
        onStop: () => {
          console.log('Audio recording stopped');
          setIsRecording(false);
          setAudioLevel(0);
        }
      });

      await recorder.start();
      setAudioRecorder(recorder);
    } catch (error) {
      console.error('Failed to start audio recording:', error);
      setIsRecording(false);
      setAudioLevel(0);

      // Handle specific error types
      const errorMessage = error instanceof Error ? error.message : String(error);
      if (errorMessage.includes('System audio capture requires user to select')) {
        await showPermissionErrorNotification('System audio capture requires you to select what to share. Please choose a tab, window, or screen when prompted.');
        setShowPermissionDialog(true);
      } else if (errorMessage.includes('No system audio track available')) {
        await showPermissionErrorNotification('No system audio track available on this OS. Please use a microphone.');
      } else if (errorMessage.includes('Permission denied')) {
        await showPermissionErrorNotification('Microphone permission denied. Please allow microphone access in your browser settings.');
      } else if (errorMessage.includes('Could not start audio source')) {
        await showPermissionErrorNotification('Audio source is busy. Please wait a moment and try again.');
      } else {
        await showPermissionErrorNotification(errorMessage || 'Failed to start audio recording');
      }
    } finally {
      audioRecordingInProgress.current = false;
    }
  };

  const stopAudioRecording = async () => {
    if (audioRecorder) {
      await audioRecorder.stop();
      setAudioRecorder(null);
    }
    audioRecordingInProgress.current = false;
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopAudioRecording();
    };
  }, []);

  const handleModeToggle = async (mode: 'typing' | 'subtitle') => {
    console.log('[FRONTEND] handleModeToggle called with mode:', mode);

    console.log('[FRONTEND] Checking actionInProgress and audioRecordingInProgress');
    if (actionInProgress.current || audioRecordingInProgress.current) {
      console.warn('[FRONTEND] Action or audio recording already in progress. Ignoring click.');
      return;
    }
    actionInProgress.current = true;
    console.log('[FRONTEND] Set actionInProgress to true');

    try {
      if (!selectedAudioDeviceRef.current) {
        console.warn('[FRONTEND] Please select an audio device first');
        return;
      }

      const isActive = mode === 'typing' ? voiceTypingActiveRef.current : liveSubtitleActiveRef.current;
      const setActive = mode === 'typing' ? setVoiceTypingActive : setLiveSubtitleActive;
      const setOtherActive = mode === 'typing' ? setLiveSubtitleActive : setVoiceTypingActive;

      console.log('[FRONTEND] Current mode active state:', isActive);
      if (isActive) {
        // Deactivation logic
        console.log('[FRONTEND] Deactivating mode:', mode);
        setIsDisconnecting(true);
        setActive(false);
        await stopAudioRecording();
        if (typeof window !== 'undefined' && (window as any).electronAPI) {
          await (window as any).electronAPI.disconnectGateway();
        }
      } else {
        // Activation logic
        console.log('[FRONTEND] Activating mode:', mode);
        setIsConnecting(true);
        setConnectionError(null);
        try {
          if (typeof window !== 'undefined' && (window as any).electronAPI) {
            setActive(true);
            setOtherActive(false);

            // Use token from ref (immediate), or fallback to localStorage
            const tokenToUse = currentTokenRef.current || authToken || localStorage.getItem('auth_token');
            const connectResult = await (window as any).electronAPI.connectGateway(tokenToUse);
            if (!connectResult.success) {
              showConnectionNotification('Cannot connect to gateway. Make sure the gateway service is running.');
              setActive(false);
              await stopAudioRecording();
              return;
            }

            const modeResult = await (window as any).electronAPI.setMode(mode);
            if (!modeResult.success) {
              showConnectionNotification(modeResult.error || 'Failed to switch mode');
              setActive(false);
              await stopAudioRecording();
              return;
            }
            await startAudioRecording();
          }
        } catch (error) {
          console.error(`[FRONTEND] Failed to connect to gateway for mode ${mode}:`, error);
          showConnectionNotification('Cannot connect to gateway. Make sure the gateway service is running.');
          setActive(false);
          await stopAudioRecording();
        }
      }
    } finally {
      setIsConnecting(false);
      setIsDisconnecting(false);
      actionInProgress.current = false;
    }
  };


  // No longer needed - using fixed window height with CSS Grid animations

  // Debounced mode toggle function for keyboard shortcuts
  const debouncedModeToggle = useRef(async (mode: 'typing' | 'subtitle') => {
    console.log('[FRONTEND] debouncedModeToggle called with mode:', mode);
    const now = Date.now();
    if (now - lastClickTime.current < 100) { // Reduced debounce for keyboard shortcuts
      console.warn('[FRONTEND] Action too soon after previous action, ignoring.');
      return;
    }
    lastClickTime.current = now;
    console.log('[FRONTEND] Calling handleModeToggle with mode:', mode);
    await handleModeToggle(mode);
  });

  useEffect(() => {
    console.log('[FRONTEND] Global shortcut useEffect running');
    // Listen for global shortcut events from Electron main process
    if (typeof window !== 'undefined' && (window as any).electronAPI) {
      console.log('[FRONTEND] electronAPI available, setting up global shortcut listener');

      const handleGlobalShortcut = async (event: any, action: string) => {
        console.log('[FRONTEND] Received global shortcut:', action);

        // Prevent multiple simultaneous shortcut processing
        if (shortcutInProgress.current) {
          console.log('[FRONTEND] Shortcut already in progress, ignoring');
          return;
        }
        shortcutInProgress.current = true;

        try {
          if (action === 'toggle-voice-typing' || action === 'voice-typing') {
            console.log('[FRONTEND] Processing toggle-voice-typing shortcut');
            console.log('[FRONTEND] selectedAudioDeviceRef.current:', selectedAudioDeviceRef.current);
            if (!selectedAudioDeviceRef.current) {
              console.warn('[FRONTEND] No audio device selected for toggle-voice-typing shortcut');
              return;
            }

            // Check if system audio is selected (requires user gesture)
            if (selectedAudioDeviceRef.current === 'system-audio') {
              console.log('[FRONTEND] System audio selected, showing notification');
              // Show the main window if it's hidden
              if (typeof window !== 'undefined' && (window as any).electronAPI) {
                (window as any).electronAPI.showWindow();
                (window as any).electronAPI.showNotification('⚠️ Sorry!', 'This shortcut can\'t be used while capturing system audio. Please click the button on screen to start instead.');
              }
              return;
            }

            console.log('[FRONTEND] Audio device available, triggering voice-typing mode toggle');
            // Use the same mode toggle logic for consistency
            await debouncedModeToggle.current('typing');
          } else if (action === 'toggle-live-subtitle' || action === 'live-subtitle') {
            console.log('[FRONTEND] Processing toggle-live-subtitle shortcut');
            console.log('[FRONTEND] selectedAudioDeviceRef.current:', selectedAudioDeviceRef.current);
            if (!selectedAudioDeviceRef.current) {
              console.warn('[FRONTEND] No audio device selected for toggle-live-subtitle shortcut');
              return;
            }

            // Check if system audio is selected (requires user gesture)
            if (selectedAudioDeviceRef.current === 'system-audio') {
              console.log('[FRONTEND] System audio selected, showing notification');
              // Show the main window if it's hidden
              if (typeof window !== 'undefined' && (window as any).electronAPI) {
                (window as any).electronAPI.showWindow();
                (window as any).electronAPI.showNotification('⚠️ Sorry!', 'This shortcut can\'t be used while capturing system audio. Please click the button on screen to start instead.');
              }
              return;
            }

            console.log('[FRONTEND] Audio device available, triggering live-subtitle mode toggle');
            // Use the same mode toggle logic for consistency
            await debouncedModeToggle.current('subtitle');
          } else if (action === 'hide-window') {
            console.log('[FRONTEND] Processing hide-window shortcut');
            if (typeof window !== 'undefined' && (window as any).electronAPI) {
              (window as any).electronAPI.hideWindow();
            }
          } else if (action === 'show-window') {
            console.log('[FRONTEND] Processing show-window shortcut');
            if (typeof window !== 'undefined' && (window as any).electronAPI) {
              (window as any).electronAPI.showWindow();
            }
          } else {
            console.log('[FRONTEND] Unknown shortcut action:', action);
          }
        } finally {
          // Reset the flag after processing
          setTimeout(() => {
            shortcutInProgress.current = false;
          }, 100); // Small delay to prevent rapid-fire triggers
        }
      };

      (window as any).electronAPI.onGlobalShortcut(handleGlobalShortcut);
      console.log('[FRONTEND] Global shortcut listener registered');

      return () => {
        console.log('[FRONTEND] Cleaning up global shortcut listener');
        // Cleanup listener
        if (typeof window !== 'undefined' && (window as any).electronAPI) {
          (window as any).electronAPI.removeAllListeners('global-shortcut');
        }
      };
    } else {
      console.log('[FRONTEND] electronAPI not available in global shortcut useEffect');
    }
  }, []) // Remove dependencies that cause re-registration issues

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
  }

  const languages = [
    { value: "en", label: "EN" },
    { value: "es", label: "ES" },
    { value: "fr", label: "FR" },
    { value: "de", label: "DE" },
    { value: "vi", label: "VI" },
    { value: "zh", label: "ZH" },
    { value: "ja", label: "JA" },
    { value: "hi", label: "HI" },
  ]

  const getStatusInfo = () => {
    const running = isRecording || voiceTypingActive || liveSubtitleActive
    const connected = isConnected
    const listening = isListening

    if (running && connected && listening) {
      return {
        text: "Listening",
        color: "text-green-400",
        bgColor: "bg-green-900/30",
        borderColor: "border-green-400",
      }
    } else if (running && connected) {
      return {
        text: "Listening",
        color: "text-yellow-400",
        bgColor: "bg-yellow-900/30",
        borderColor: "border-yellow-400",
      }
    } else if (running && !connected) {
      return {
        text: "Connecting",
        color: "text-yellow-400",
        bgColor: "bg-yellow-900/30",
        borderColor: "border-yellow-400",
      }
    } else if (connected) {
      return {
        text: "Connected",
        color: "text-blue-400",
        bgColor: "bg-blue-900/30",
        borderColor: "border-blue-400",
      }
    } else {
      return {
        text: "Inactive",
        color: "text-slate-400",
        bgColor: "bg-slate-800/30",
        borderColor: "border-slate-600",
      }
    }
  }

  const statusInfo = getStatusInfo()

  return (
    <div
      ref={rootRef}
      className="dynamic-container"
      style={{
        background: 'transparent',
        width: '1050px',
        height: 'max-content',
        margin: 0,
        padding: 0      }}
      id="nova-root"
    >
      <div ref={toolbarRef} className="flex justify-center">
        <div className="bg-slate-900/70 backdrop-blur-md border border-slate-700/30 rounded-2xl shadow-2xl w-full drag-region">
          <div className="flex items-center justify-between py-2 pl-4 pr-2 gap-2">
            <div className="flex items-center gap-1 flex-1 justify-start no-drag-region">
              <Button
                variant="outline"
                size="sm"
                className={`px-1.5 py-1 border-slate-600 text-slate-300 hover:bg-slate-700 bg-transparent relative transition-all duration-200 min-w-[90px] no-drag-region ${
                  voiceTypingActive ? "shadow-md shadow-blue-500/50 border-blue-400 text-blue-300 bg-blue-900/30" : ""
                }`}
                onClick={() => handleModeToggle('typing')}
              >
                <Type className="w-2.5 h-2.5 mr-0.5" />
                <span className="text-[10px]">Voice Typing</span>
                <span className="text-slate-500 text-[8px] ml-0.5">Win+Alt+V</span>
                {voiceTypingActive && (
                  <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
                )}
              </Button>

              <Button
                variant="outline"
                size="sm"
                className={`px-1.5 py-1 border-slate-600 text-slate-300 hover:bg-slate-700 bg-transparent relative transition-all duration-200 min-w-[90px] ${
                  liveSubtitleActive
                    ? "shadow-md shadow-green-500/50 border-green-400 text-green-300 bg-green-900/30"
                    : ""
                }`}
                onClick={() => handleModeToggle('subtitle')}
              >
                <Subtitles className="w-2.5 h-2.5 mr-0.5" />
                <span className="text-[10px]">Live Subtitle</span>
                <span className="text-slate-500 text-[8px] ml-0.5">Win+Alt+L</span>
                {liveSubtitleActive && (
                  <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
                )}
              </Button>

            </div>

            <div className="flex items-center gap-2 flex-shrink-0 no-drag-region">
              <div className="flex items-center gap-1">
                <Select 
                  value={sourceLanguage} 
                  onValueChange={setSourceLanguage}
                  open={openDropdown === 'source'}
                  onOpenChange={(open: boolean) => {
                    if (open) {
                      setPendingDropdown('source')
                    } else {
                      setOpenDropdown(null)
                      setPendingDropdown(null)
                    }
                  }}
                >
                  <SelectTrigger className="w-18 h-6 bg-slate-800/50 border-slate-600 text-white text-xs">
                    <SelectValue placeholder="EN" />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-600">
                    {languages.map((lang) => (
                      <SelectItem key={lang.value} value={lang.value} className="text-white hover:bg-slate-700 text-xs">
                        {lang.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <span className="text-slate-400 text-[10px]">→</span>
                <Select 
                  value={targetLanguage} 
                  onValueChange={setTargetLanguage}
                  open={openDropdown === 'target'}
                  onOpenChange={(open: boolean) => {
                    if (open) {
                      setPendingDropdown('target')
                    } else {
                      setOpenDropdown(null)
                      setPendingDropdown(null)
                    }
                  }}
                >
                  <SelectTrigger className="w-18 h-6 bg-slate-800/50 border-slate-600 text-white text-xs">
                    <SelectValue placeholder="VI" />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-800 border-slate-600">
                    {languages.map((lang) => (
                      <SelectItem key={lang.value} value={lang.value} className="text-white hover:bg-slate-700 text-xs">
                        {lang.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="w-[130px]">
                <AudioDeviceSelector
                  value={selectedAudioDevice}
                  onValueChange={setSelectedAudioDevice}
                  placeholder="Select audio source"
                  className="h-6 text-xs"
                  open={openDropdown === 'audio'}
                  onOpenChange={(open: boolean) => {
                    if (open) {
                      setPendingDropdown('audio')
                    } else {
                      setOpenDropdown(null)
                      setPendingDropdown(null)
                    }
                  }}
                />
              </div>
            </div>

            <div className="flex items-center justify-center flex-shrink-0 no-drag-region">
              <Button
                variant="outline"
                size="sm"
                className={`px-1.5 py-1 w-[90px] ${statusInfo.borderColor} ${statusInfo.color} hover:bg-slate-700 ${statusInfo.bgColor} transition-all duration-200`}
              >
                <Activity className="w-2.5 h-2.5 mr-0.5" />
                <span className="text-[10px]">{statusInfo.text}</span>
              </Button>
            </div>

            <div className="flex items-center justify-center flex-shrink-0 no-drag-region">
              <Button
                variant="outline"
                size="sm"
                className="px-1.5 py-1 border-slate-600 text-slate-300 hover:bg-slate-700 bg-transparent transition-all duration-200"
                onClick={() => {
                  if (typeof window !== 'undefined' && (window as any).electronAPI) {
                    (window as any).electronAPI.hideWindow();
                  }
                }}
              >
                <EyeOff className="w-2.5 h-2.5 mr-0.5" />
                <span className="text-[10px]">Hide</span>
                <span className="text-slate-500 text-[8px] ml-0.5">Win+Alt+H</span>
              </Button>
            </div>

            <div className="flex items-center gap-1 flex-1 justify-end no-drag-region">
              <Button
                variant="outline"
                size="sm"
                className="px-1.5 py-1 border-slate-600 text-slate-300 hover:bg-slate-700 bg-transparent transition-all duration-200"
                onClick={async () => {
                  setIsRecording(false)
                  setRecordingTime(0)
                  setVoiceTypingActive(false)
                  setLiveSubtitleActive(false)
                  setLiveTranscriptionText('')
                  setConnectionError(null)
                  await stopAudioRecording()

                  // Send start over command before disconnecting
                  if (typeof window !== 'undefined' && (window as any).electronAPI) {
                    (window as any).electronAPI.sendStartOver();
                    (window as any).electronAPI.disconnectGateway();
                  }
                }}
              >
                <RotateCcw className="w-2.5 h-2.5 mr-0.5" />
                <span className="text-[10px]">Start Over</span>
              </Button>



              <div className="flex items-center gap-0.5">
                <Button
                  variant="ghost"
                  size="sm"
                  className="p-1 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-all duration-200"
                  onClick={() => setShowSettings(!showSettings)}
                >
                  <Settings className="w-2.5 h-2.5" />
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  className="p-1 text-slate-400 hover:text-red-400 hover:bg-red-900/20 rounded-lg transition-all duration-200"
                  onClick={() => {
                    if (typeof window !== 'undefined' && (window as any).electronAPI) {
                      (window as any).electronAPI.quitApp();
                    }
                  }}
                >
                  <X className="w-2.5 h-2.5" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Connection Error Display */}
      {connectionError && (
        <div className="fixed top-4 left-4 right-4 bg-red-900/90 backdrop-blur-md border border-red-700/50 rounded-xl p-4 shadow-2xl z-50">
          <div className="flex items-center gap-3">
            <div className="flex-shrink-0">
              <div className="w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
                <span className="text-white text-xs">⚠</span>
              </div>
            </div>
            <div className="flex-1">
              <p className="text-red-200 text-sm font-medium">Connection Error</p>
              <p className="text-red-300 text-xs mt-1">{connectionError}</p>
            </div>
            <button
              onClick={() => setConnectionError(null)}
              className="text-red-400 hover:text-red-300 transition-colors"
            >
              ×
            </button>
          </div>
        </div>
      )}


      {/* Live transcription moved to dedicated overlay window handled by Electron */}

      <div className={`flex flex-col items-center justify-start ${showSettingsPadding || isVisible ? 'pt-2 pb-2' : ''}`} id="nova-content">
        <div className="w-full max-w-7xl">
          <div className="grid transition-all duration-500 ease-out" style={{ gridTemplateRows: showSettings ? '1fr' : '0fr' }}>
            <div className="overflow-hidden">
              <div ref={settingsRef} className={`bg-slate-900/70 backdrop-blur-md border border-slate-700/30 rounded-xl shadow-2xl ${isVisible ? 'mb-2' : ''}`}>
                <div className="py-2 px-4">
                  <div className="mb-6 flex items-center justify-between">
                    <h3 className="text-white font-semibold text-lg flex items-center">
                      <Settings className="w-5 h-5 mr-3" />
                      Settings
                    </h3>
                    <Button
                      variant="outline"
                      size="sm"
                      className="px-1.5 py-1 border-slate-600 text-slate-300 hover:bg-slate-700 bg-transparent transition-all duration-200"
                      onClick={async () => {
                        try {
                          setIsRecording(false)
                          setRecordingTime(0)
                          setVoiceTypingActive(false)
                          setLiveSubtitleActive(false)
                          setLiveTranscriptionText('')
                          setConnectionError(null)
                          await stopAudioRecording()
                          if (typeof window !== 'undefined' && (window as any).electronAPI) {
                            (window as any).electronAPI.sendStartOver();
                            (window as any).electronAPI.disconnectGateway();
                          }
                        } finally {
                          // Clear authentication state
                          setIsAuthenticated(false);
                          setUser(null);
                          setAuthToken(null);
                          localStorage.removeItem('auth_token');

                          // Call logout API if available
                          if (typeof window !== 'undefined' && (window as any).authAPI) {
                            await (window as any).authAPI.logout();
                          }
                        }
                      }}
                    >
                      <LogOut className="w-2.5 h-2.5 mr-0.5" />
                      <span className="text-[10px]">Logout</span>
                    </Button>
                  </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  <div className="space-y-6">
                    <h4 className="text-slate-300 font-medium flex items-center">
                      <Volume2 className="w-4 h-4 mr-2" />
                      Audio Devices
                    </h4>

                    <div className="space-y-4">
                      <div>
                        <label className="text-sm text-slate-400 mb-2 block">Audio Source</label>
                        <AudioDeviceSelector
                          value={selectedAudioDevice}
                          onValueChange={setSelectedAudioDevice}
                          placeholder="Select audio device"
                          className="w-full"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="space-y-6">
                    <h4 className="text-slate-300 font-medium flex items-center">
                      <Keyboard className="w-4 h-4 mr-2" />
                      Keybinds
                    </h4>

                    <div className="space-y-4">
                      <div>
                        <label className="text-sm text-slate-400 mb-2 block">Voice Typing</label>
                        <input
                          type="text"
                          value={voiceTypingKeybind}
                          onChange={(e) => setVoiceTypingKeybind(e.target.value)}
                          className="w-full h-10 px-3 bg-slate-800/50 border border-slate-600 rounded-lg text-white focus:border-blue-400 focus:outline-none transition-colors"
                          placeholder="Win+Alt+V"
                        />
                      </div>

                      <div>
                        <label className="text-sm text-slate-400 mb-2 block">Live Subtitle</label>
                        <input
                          type="text"
                          value={liveSubtitleKeybind}
                          onChange={(e) => setLiveSubtitleKeybind(e.target.value)}
                          className="w-full h-10 px-3 bg-slate-800/50 border border-slate-600 rounded-lg text-white focus:border-blue-400 focus:outline-none transition-colors"
                          placeholder="Win+Alt+L"
                        />
                      </div>

                      <div>
                        <label className="text-sm text-slate-400 mb-2 block">Hide Window</label>
                        <input
                          type="text"
                          value={hideKeybind}
                          onChange={(e) => setHideKeybind(e.target.value)}
                          className="w-full h-10 px-3 bg-slate-800/50 border border-slate-600 rounded-lg text-white focus:border-blue-400 focus:outline-none transition-colors"
                          placeholder="Win+Alt+H"
                        />
                      </div>

                    </div>
                  </div>
                  </div>
                </div>
              </div>
            </div>
          </div>


        </div>
      </div>
      
      {/* Permission Error Dialog */}
      {showPermissionDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-800 border border-slate-600 rounded-xl p-6 max-w-md mx-4">
            <h3 className="text-white font-semibold text-lg mb-4 flex items-center">
              <Settings className="w-5 h-5 mr-3" />
              System Audio Capture
            </h3>
            <p className="text-slate-300 mb-6">System audio capture uses Windows loopback. When prompted, sharing will be auto-approved.</p>
            <div className="flex gap-3">
              <Button
                onClick={() => {
                  setShowPermissionDialog(false);
                }}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                onClick={async () => {
                  setShowPermissionDialog(false);
                  setIsRequestingPermission(true);
                  try {
                    // Try to get system audio again
                    await startAudioRecording();
                  } catch (error) {
                    console.error('Permission request failed:', error);
                  } finally {
                    setIsRequestingPermission(false);
                  }
                }}
                className="flex-1"
                disabled={isRequestingPermission}
              >
                {isRequestingPermission ? 'Requesting...' : 'Try Again'}
              </Button>
            </div>
          </div>
        </div>
      )}
      

    </div>
  )
}

