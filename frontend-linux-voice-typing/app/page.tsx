"use client"

import { useEffect, useState } from "react"
import { useConnection } from "@/hooks/useConnection"
import { useAudioRecording } from "@/hooks/useAudioRecording"
import { gateway } from "@/lib/gateway"
import { audioDeviceManager, type AudioDevice } from "@/lib/audio-devices"

const LANGUAGE_OPTIONS = [
  { code: "en", label: "English" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
  { code: "de", label: "German" },
  { code: "it", label: "Italian" },
  { code: "pt", label: "Portuguese" },
  { code: "vi", label: "Vietnamese" },
  { code: "ja", label: "Japanese" },
  { code: "ko", label: "Korean" },
  { code: "zh", label: "Chinese" },
  { code: "ru", label: "Russian" },
  { code: "ar", label: "Arabic" },
  { code: "hi", label: "Hindi" },
]

export default function LinuxVoiceTypingApp() {
  const [sourceLanguage, setSourceLanguage] = useState("en")
  const [targetLanguage, setTargetLanguage] = useState("en")
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [liveText, setLiveText] = useState("")
  const [devices, setDevices] = useState<AudioDevice[]>([])
  const [loadingDevices, setLoadingDevices] = useState(false)

  const { connected, connecting, connect, disconnect, setMode } = useConnection()
  const {
    isRecording,
    selectedDevice,
    setSelectedDevice,
    startRecording,
    stopRecording
  } = useAudioRecording()

  useEffect(() => {
    const loadDevices = async () => {
      setLoadingDevices(true)
      try {
        const discovered = await audioDeviceManager.enumerateDevices()
        const inputDevices = discovered.filter((device) => device.kind === "audioinput")
        setDevices(inputDevices)
        if (!selectedDevice && inputDevices.length > 0) {
          setSelectedDevice(inputDevices[0].deviceId)
        }
      } catch (error) {
        console.error("Failed to enumerate devices", error)
      } finally {
        setLoadingDevices(false)
      }
    }

    loadDevices()

    const handleDeviceChange = () => {
      loadDevices()
    }

    navigator.mediaDevices.addEventListener("devicechange", handleDeviceChange)
    return () => {
      navigator.mediaDevices.removeEventListener("devicechange", handleDeviceChange)
    }
  }, [setSelectedDevice, selectedDevice])

  const handleStart = async () => {
    if (!selectedDevice) {
      setConnectionError("Select a microphone first")
      return
    }

    setConnectionError(null)

    const connectResult = await connect()
    if (!connectResult.success) {
      setConnectionError(connectResult.error || "Failed connecting to gateway")
      return
    }

    const modeResult = await setMode("typing")
    if (!modeResult.success) {
      setConnectionError(modeResult.error || "Failed to enter typing mode")
      await disconnect()
      return
    }

    const recordingStarted = await startRecording()
    if (!recordingStarted) {
      setConnectionError("Failed starting microphone recording")
      await disconnect()
    }
  }

  const handleStop = async () => {
    await stopRecording()
    await disconnect()
  }

  useEffect(() => {
    if (connected) {
      gateway.updateLanguages(sourceLanguage, targetLanguage)
    }
  }, [sourceLanguage, targetLanguage, connected])

  useEffect(() => {
    const handleRealtimeResult = (_event: unknown, data: Record<string, unknown>) => {
      const transcription = (data.text as string) || ""
      const translation = (data.translation as string) || ""
      const preview = sourceLanguage === targetLanguage ? transcription : (translation || transcription)
      setLiveText(preview)
    }

    window.electronAPI.onRealtimeResult(handleRealtimeResult)
    return () => {
      window.electronAPI.removeAllListeners("realtime-result")
    }
  }, [sourceLanguage, targetLanguage])

  return (
    <main className="w-[560px] bg-slate-950 text-slate-100 border border-slate-800 rounded-xl shadow-2xl p-5">
      <div className="mb-4">
        <h1 className="text-lg font-semibold">Nova Voice Typing (Linux)</h1>
        <p className="text-xs text-slate-400 mt-1">
          Minimal mode: microphone -> gateway -> auto typing
        </p>
      </div>

      {connectionError && (
        <div className="mb-4 rounded-lg border border-red-700/60 bg-red-950/60 px-3 py-2 text-sm text-red-200">
          {connectionError}
        </div>
      )}

      <div className="space-y-3">
        <label className="block">
          <span className="text-xs text-slate-400">Microphone</span>
          <div className="flex gap-2 mt-1">
            <select
              className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              value={selectedDevice}
              onChange={(event) => setSelectedDevice(event.target.value)}
              disabled={loadingDevices || isRecording}
            >
              {devices.length === 0 && (
                <option value="">
                  {loadingDevices ? "Loading devices..." : "No microphone devices found"}
                </option>
              )}
              {devices.map((device) => (
                <option key={device.deviceId} value={device.deviceId}>
                  {device.label}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="rounded-md border border-slate-700 bg-slate-900 px-3 text-sm hover:bg-slate-800"
              onClick={async () => {
                setLoadingDevices(true)
                try {
                  const discovered = await audioDeviceManager.enumerateDevices()
                  setDevices(discovered.filter((device) => device.kind === "audioinput"))
                } finally {
                  setLoadingDevices(false)
                }
              }}
              disabled={loadingDevices || isRecording}
            >
              Refresh
            </button>
          </div>
        </label>

        <div className="grid grid-cols-2 gap-3">
          <label className="block">
            <span className="text-xs text-slate-400">Source language</span>
            <select
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              value={sourceLanguage}
              onChange={(event) => setSourceLanguage(event.target.value)}
              disabled={isRecording}
            >
              {LANGUAGE_OPTIONS.map((language) => (
                <option key={language.code} value={language.code}>
                  {language.label}
                </option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-xs text-slate-400">Target language</span>
            <select
              className="mt-1 w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              value={targetLanguage}
              onChange={(event) => setTargetLanguage(event.target.value)}
              disabled={isRecording}
            >
              {LANGUAGE_OPTIONS.map((language) => (
                <option key={language.code} value={language.code}>
                  {language.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="flex items-center gap-2 pt-2">
          {!isRecording ? (
            <button
              type="button"
              onClick={handleStart}
              disabled={connecting || !selectedDevice}
              className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
            >
              {connecting ? "Connecting..." : "Start Voice Typing"}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleStop}
              className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium hover:bg-red-500"
            >
              Stop
            </button>
          )}
          <button
            type="button"
            onClick={() => window.electronAPI.quitApp()}
            className="rounded-md border border-slate-700 bg-slate-900 px-4 py-2 text-sm hover:bg-slate-800"
          >
            Quit
          </button>
        </div>

        <div className="rounded-md border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm">
          <div className="mb-1 text-xs text-slate-400">Status</div>
          <div className="text-slate-200">
            {isRecording && connected ? "Typing active" : connected ? "Connected" : "Disconnected"}
          </div>
        </div>

        <div className="rounded-md border border-slate-800 bg-slate-900/70 px-3 py-2">
          <div className="mb-1 text-xs text-slate-400">Live text preview</div>
          <p className="min-h-[64px] text-sm text-slate-200 whitespace-pre-wrap break-words">
            {liveText || "Start voice typing to preview recognized text."}
          </p>
        </div>
      </div>
    </main>
  )
}
