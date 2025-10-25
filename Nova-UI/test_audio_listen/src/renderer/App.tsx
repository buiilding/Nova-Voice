import React, { useEffect, useMemo, useRef, useState } from 'react'

type AudioDevice = {
  deviceId: string
  label: string
}

function useAudioMeter(stream: MediaStream | null) {
  const [level, setLevel] = useState(0)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    if (!stream) {
      setLevel(0)
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      analyserRef.current?.disconnect()
      analyserRef.current = null
      return
    }
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
    const source = audioContext.createMediaStreamSource(stream)
    const analyser = audioContext.createAnalyser()
    analyser.fftSize = 512
    source.connect(analyser)
    analyserRef.current = analyser
    const data = new Uint8Array(analyser.frequencyBinCount)

    const loop = () => {
      analyser.getByteTimeDomainData(data)
      let sum = 0
      for (let i = 0; i < data.length; i++) {
        const v = (data[i] - 128) / 128
        sum += v * v
      }
      const rms = Math.sqrt(sum / data.length)
      setLevel(rms)
      rafRef.current = requestAnimationFrame(loop)
    }
    rafRef.current = requestAnimationFrame(loop)

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      source.disconnect()
      analyser.disconnect()
      audioContext.close()
    }
  }, [stream])

  return level
}

async function listMicrophones(): Promise<AudioDevice[]> {
  const devices = await navigator.mediaDevices.enumerateDevices()
  return devices
    .filter(d => d.kind === 'audioinput')
    .map(d => ({ deviceId: d.deviceId, label: d.label || 'Microphone' }))
}

export default function App() {
  const [micDevices, setMicDevices] = useState<AudioDevice[]>([])
  const [renderDevices, setRenderDevices] = useState<{ id: string; name: string }[]>([])
  const [selectedRender, setSelectedRender] = useState<string>('')
  const [selectedMic, setSelectedMic] = useState<string>('')
  const [micStream, setMicStream] = useState<MediaStream | null>(null)
  const [systemStream, setSystemStream] = useState<MediaStream | null>(null)
  const [error, setError] = useState<string>('')

  const micLevel = useAudioMeter(micStream)
  const sysLevel = useAudioMeter(systemStream)

  useEffect(() => {
    // Initial device enumeration requires prior getUserMedia in some browsers to reveal labels
    navigator.mediaDevices.getUserMedia({ audio: true })
      .catch(() => {})
      .finally(async () => {
        const mics = await listMicrophones()
        setMicDevices(mics)
        if (mics.length && !selectedMic) setSelectedMic(mics[0].deviceId)
        // Enumerate Windows MMDevice endpoints if native addon available
        const endpoints = (window as any).electronAPI?.enumerateAudioEndpoints?.() || { capture: [], render: [] }
        const renders = endpoints.render || []
        setRenderDevices(renders)
        if (renders.length && !selectedRender) setSelectedRender(renders[0].id)
      })
  }, [])

  async function startMic() {
    try {
      if (micStream) stopMic()
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: selectedMic ? { deviceId: { exact: selectedMic } } as MediaTrackConstraints : true
      })
      setMicStream(stream)
      setError('')
    } catch (e: any) {
      setError('Failed to start microphone: ' + (e?.message || e))
    }
  }

  function stopMic() {
    micStream?.getTracks().forEach(t => t.stop())
    setMicStream(null)
  }

  async function startSystem() {
    try {
      if (systemStream) stopSystem()
      // Uses Electron's session.setDisplayMediaRequestHandler to auto-pick a screen with loopback audio on Windows
      const stream = await (navigator.mediaDevices as any).getDisplayMedia({
        // Some environments require requesting video to allow display-capture audio
        video: { frameRate: 1 },
        audio: true
      })
             // Do not stop the video track; stopping it can end the capture (and audio) in some implementations
       if (!stream.getAudioTracks || stream.getAudioTracks().length === 0) {
         throw new Error('No system audio track available on this OS')
       }
       // Note: Selecting a specific render endpoint for loopback is not exposed via getDisplayMedia.
       // The selected output device (render endpoint) is shown for user context only.
       setSystemStream(stream)
       setError('')
    } catch (e: any) {
      setError('Failed to start system audio: ' + (e?.message || e))
    }
  }

  function stopSystem() {
    systemStream?.getTracks().forEach(t => t.stop())
    setSystemStream(null)
  }

  const micPct = useMemo(() => Math.min(100, Math.round(micLevel * 200)), [micLevel])
  const sysPct = useMemo(() => Math.min(100, Math.round(sysLevel * 200)), [sysLevel])

  return (
    <div style={{ fontFamily: 'sans-serif', padding: 16 }}>
      <h2>Audio Listener</h2>
      {error && <div style={{ color: 'red', marginBottom: 8 }}>{error}</div>}

      <section style={{ marginBottom: 16 }}>
        <h3>Microphone</h3>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <select
            value={selectedMic}
            onChange={(e) => setSelectedMic(e.target.value)}
            style={{ minWidth: 240 }}
          >
            {micDevices.map(d => (
              <option key={d.deviceId} value={d.deviceId}>{d.label}</option>
            ))}
          </select>
          <button onClick={startMic}>Start Mic</button>
          <button onClick={stopMic} disabled={!micStream}>Stop Mic</button>
          <div style={{ width: 140, height: 10, background: '#eee', position: 'relative' }}>
            <div style={{ width: `${micPct}%`, height: '100%', background: '#4caf50' }} />
          </div>
        </div>
      </section>

      <section>
        <h3>System Audio (Windows loopback)</h3>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {renderDevices.length > 0 && (
            <select
              value={selectedRender}
              onChange={(e) => setSelectedRender(e.target.value)}
              style={{ minWidth: 260 }}
            >
              {renderDevices.map(d => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          )}
          <button onClick={startSystem}>Start System Audio</button>
          <button onClick={stopSystem} disabled={!systemStream}>Stop System Audio</button>
          <div style={{ width: 140, height: 10, background: '#eee', position: 'relative' }}>
            <div style={{ width: `${sysPct}%`, height: '100%', background: '#2196f3' }} />
          </div>
        </div>
      </section>

    </div>
  )
}


