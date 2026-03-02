import { useState, useEffect, useRef, useCallback } from 'react';
import { AudioRecorder } from '@/lib/audio-recorder';
import { audioDeviceManager } from '@/lib/audio-devices';

export function useAudioRecording() {
  const [isRecording, setIsRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [selectedDevice, setSelectedDevice] = useState<string>('');
  const [audioRecorder, setAudioRecorder] = useState<AudioRecorder | null>(null);

  const recordingRef = useRef(false);

  useEffect(() => {
    recordingRef.current = isRecording;
  }, [isRecording]);

  const startRecording = useCallback(async () => {
    if (!selectedDevice || isRecording) return false;

    try {
      // Stop any existing recording
      if (audioRecorder) {
        await audioRecorder.stop();
        setAudioRecorder(null);
      }

      // Get device stream
      const device = await audioDeviceManager.getDeviceStream(selectedDevice);
      if (!device) return false;

      const recorder = new AudioRecorder({
        deviceId: selectedDevice,
        sampleRate: 16000,
        channels: 1,
        onData: (audioData: Float32Array) => {
          // UI level meter
          const level = AudioRecorder.getAudioLevel(audioData);
          setAudioLevel(level);

          // Convert to Int16 for server transmission
          const int16Data = AudioRecorder.float32ToInt16(audioData);
          const uint8Array = new Uint8Array(int16Data.buffer.slice(0));

          // Send to gateway
          if (typeof window !== 'undefined' && window.electronAPI) {
            if (!recordingRef.current) return;
            const sr = (recorder as any)?.getSampleRate ? (recorder as any).getSampleRate() : 16000;
            if (window.electronAPI.sendAudioChunk) {
              window.electronAPI.sendAudioChunk(uint8Array, sr || 16000);
            } else {
              window.electronAPI.sendAudioData(uint8Array, sr || 16000);
            }
          }
        },
        onError: (error) => {
          console.error('Audio recording error:', error);
          setIsRecording(false);
          setAudioLevel(0);
        },
        onStart: () => {
          setIsRecording(true);
        },
        onStop: () => {
          setIsRecording(false);
          setAudioLevel(0);
        }
      });

      await recorder.start();
      setAudioRecorder(recorder);
      return true;
    } catch (error) {
      console.error('Failed to start audio recording:', error);
      setIsRecording(false);
      setAudioLevel(0);
      return false;
    }
  }, [selectedDevice, isRecording, audioRecorder]);

  const stopRecording = useCallback(async () => {
    if (audioRecorder) {
      await audioRecorder.stop();
      setAudioRecorder(null);
    }
  }, [audioRecorder]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioRecorder) {
        audioRecorder.stop();
      }
    };
  }, [audioRecorder]);

  return {
    isRecording,
    audioLevel,
    selectedDevice,
    setSelectedDevice,
    startRecording,
    stopRecording,
  };
}
