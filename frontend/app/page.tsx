"use client"

import { useState, useEffect } from "react"
import { ModeButtons } from "@/components/control/ModeButtons"
import { LangSelectors } from "@/components/control/LangSelectors"
import { AudioSource } from "@/components/control/AudioSource"
import { StatusIndicator } from "@/components/control/StatusIndicator"
import { TopBar } from "@/components/control/TopBar"
import { SettingsPanel } from "@/components/settings/SettingsPanel"
import { useConnection } from "@/hooks/useConnection"
import { useAudioRecording } from "@/hooks/useAudioRecording"
import { useShortcuts } from "@/hooks/useShortcuts"
import { useWindowSizing } from "@/hooks/useWindowSizing"
import { gateway } from "@/lib/gateway"

export default function VoiceTranscriberApp() {
  // State management using hooks
  const [sourceLanguage, setSourceLanguage] = useState("en")
  const [targetLanguage, setTargetLanguage] = useState("vi")
  const [voiceTypingKeybind, setVoiceTypingKeybind] = useState("Win+Alt+V")
  const [liveSubtitleKeybind, setLiveSubtitleKeybind] = useState("Win+Alt+L")
  const [hideKeybind, setHideKeybind] = useState("Win+Alt+H")
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [liveTranscriptionText, setLiveTranscriptionText] = useState("")
  const [openDropdown, setOpenDropdown] = useState<'source' | 'target' | 'audio' | null>(null)
  const [pendingDropdown, setPendingDropdown] = useState<'source' | 'target' | 'audio' | null>(null)

  // Custom hooks
  const { connected, connecting, mode, connect, disconnect, setMode } = useConnection()
  const {
    isRecording,
    audioLevel,
    selectedDevice,
    setSelectedDevice,
    startRecording,
    stopRecording
  } = useAudioRecording()
  const {
    rootRef,
    toolbarRef,
    settingsRef,
    showSettings,
    toggleSettings,
  } = useWindowSizing(openDropdown, pendingDropdown)

  // Handle pending dropdown opening after window resize
  useEffect(() => {
    if (pendingDropdown && openDropdown === null) {
      const timer = setTimeout(() => {
        setOpenDropdown(pendingDropdown);
        setPendingDropdown(null);
      }, 100); // Small delay to ensure window resize completes

      return () => clearTimeout(timer);
    }
  }, [pendingDropdown, openDropdown]);

  // Determine active states based on connection mode
  const voiceTypingActive = connected && mode === 'typing' && isRecording
  const liveSubtitleActive = connected && mode === 'subtitle' && isRecording
  const isListening = isRecording && connected

  // Handle mode toggles
  const handleModeToggle = async (newMode: 'typing' | 'subtitle') => {
    if (!selectedDevice) {
      setConnectionError('Please select an audio device first')
      return
    }

    const isActive = newMode === 'typing' ? voiceTypingActive : liveSubtitleActive

    if (isActive) {
      // Deactivate
      await stopRecording()
      await disconnect()
    } else {
      // Activate
      setConnectionError(null)

      // Connect to gateway first
      const connectResult = await connect()
      if (!connectResult.success) {
        setConnectionError(connectResult.error || 'Failed to connect to gateway')
        return
      }

      // Set mode
      const modeResult = await setMode(newMode)
      if (!modeResult.success) {
        setConnectionError(modeResult.error || 'Failed to set mode')
        await disconnect()
        return
      }

      // Start recording
      const recordingStarted = await startRecording()
      if (!recordingStarted) {
        setConnectionError('Failed to start audio recording')
        await disconnect()
      }
    }
  }

  // Handle shortcuts
  useShortcuts(async (action) => {
    switch (action) {
      case 'toggle-voice-typing':
      case 'voice-typing':
        if (!selectedDevice) return
        if (selectedDevice === 'system-audio') {
          window.electronAPI.showNotification('⚠️ Sorry!', 'This shortcut can\'t be used while capturing system audio. Please click the button on screen to start instead.')
          window.electronAPI.showWindow()
          return
        }
        await handleModeToggle('typing')
        break
      case 'toggle-live-subtitle':
      case 'live-subtitle':
        if (!selectedDevice) return
        if (selectedDevice === 'system-audio') {
          window.electronAPI.showNotification('⚠️ Sorry!', 'This shortcut can\'t be used while capturing system audio. Please click the button on screen to start instead.')
          window.electronAPI.showWindow()
          return
        }
        await handleModeToggle('subtitle')
        break
      case 'hide-window':
        window.electronAPI.hideWindow()
        break
      case 'show-window':
        window.electronAPI.showWindow()
        break
    }
  })

  // Update languages when they change
  useEffect(() => {
    if (connected) {
      gateway.updateLanguages(sourceLanguage, targetLanguage)
    }
  }, [sourceLanguage, targetLanguage, connected])

  // Setup real-time event listeners
  useEffect(() => {
    const handleRealtimeResult = (_event: any, data: any) => {
      if (liveSubtitleActive) {
        const transcriptionText = data.text || ''
        const translationText = data.translation || ''

        const translationEnabled = sourceLanguage !== targetLanguage
          if (translationEnabled) {
          window.electronAPI.updateDualSubtitle({
              transcription: transcriptionText,
              translation: translationText
          })
          } else {
          const displayText = translationText || transcriptionText
          window.electronAPI.updateSubtitle(displayText)
        }
      }
    }

    const handleLiveTranscriptionUpdate = (_event: any, data: any) => {
      const displayText = data.translation || data.text || ''
      setLiveTranscriptionText(displayText)
    }

    window.electronAPI.onRealtimeResult(handleRealtimeResult)
    window.electronAPI.onLiveTranscriptionUpdate(handleLiveTranscriptionUpdate)

    return () => {
      window.electronAPI.removeAllListeners('realtime-result')
      window.electronAPI.removeAllListeners('live-transcription-update')
    }
  }, [liveSubtitleActive, sourceLanguage, targetLanguage])

  // Handle start over
  const handleStartOver = async () => {
    setConnectionError(null)
    setLiveTranscriptionText('')
    await stopRecording()
    await disconnect()
    await gateway.startOver()
  }

  return (
    <div
      ref={rootRef}
      className="dynamic-container"
      style={{
        background: 'transparent',
        width: '1050px',
        height: 'max-content',
        margin: 0,
        padding: 0
      }}
      id="nova-root"
    >
      <div ref={toolbarRef} className="flex justify-center">
        <div className="bg-slate-900/70 backdrop-blur-md border border-slate-700/30 rounded-2xl shadow-2xl w-full drag-region">
          <div className="flex items-center justify-between py-2 pl-4 pr-2 gap-2">
            <div className="flex items-center gap-2">
              <ModeButtons
                voiceTypingActive={voiceTypingActive}
                liveSubtitleActive={liveSubtitleActive}
                onToggleVoiceTyping={() => handleModeToggle('typing')}
                onToggleLiveSubtitle={() => handleModeToggle('subtitle')}
              />

              <LangSelectors
                sourceLanguage={sourceLanguage}
                targetLanguage={targetLanguage}
                onSourceLanguageChange={setSourceLanguage}
                onTargetLanguageChange={setTargetLanguage}
                openDropdown={openDropdown}
                setOpenDropdown={setOpenDropdown}
                setPendingDropdown={setPendingDropdown}
              />

              <AudioSource
                selectedAudioDevice={selectedDevice}
                onAudioDeviceChange={setSelectedDevice}
                openDropdown={openDropdown}
                setOpenDropdown={setOpenDropdown}
                setPendingDropdown={setPendingDropdown}
              />
            </div>

            <div className="flex items-center gap-2">
              <StatusIndicator
                running={isRecording}
                connected={connected}
                listening={isListening}
              />

              <TopBar
                showSettings={showSettings}
                onToggleSettings={toggleSettings}
                onStartOver={handleStartOver}
                onHideWindow={() => window.electronAPI.hideWindow()}
                onQuitApp={() => window.electronAPI.quitApp()}
              />
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

      <div className={`flex flex-col items-center justify-start ${showSettings ? 'pt-2 pb-2' : ''}`} id="nova-content">
        <div className="w-full max-w-7xl">
          <div className="grid transition-all duration-500 ease-out" style={{ gridTemplateRows: showSettings ? '1fr' : '0fr' }}>
            <div className="overflow-hidden">
              <div ref={settingsRef}>
                <SettingsPanel
                  selectedAudioDevice={selectedDevice}
                  onAudioDeviceChange={setSelectedDevice}
                  voiceTypingKeybind={voiceTypingKeybind}
                  liveSubtitleKeybind={liveSubtitleKeybind}
                  hideKeybind={hideKeybind}
                  onVoiceTypingKeybindChange={setVoiceTypingKeybind}
                  onLiveSubtitleKeybindChange={setLiveSubtitleKeybind}
                  onHideKeybindChange={setHideKeybind}
                  onStartOver={handleStartOver}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

