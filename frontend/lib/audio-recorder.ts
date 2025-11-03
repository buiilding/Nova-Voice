export interface AudioRecorderOptions {
  deviceId: string;
  sampleRate?: number;
  channels?: number;
  onData?: (audioData: Float32Array) => void;
  onError?: (error: Error) => void;
  onStart?: () => void;
  onStop?: () => void;
}

export class AudioRecorder {
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private sourceNode: MediaStreamAudioSourceNode | null = null;
  private scriptNode: ScriptProcessorNode | null = null; // Changed from AnalyserNode
  private isRecording = false;
  private options: AudioRecorderOptions;

  constructor(options: AudioRecorderOptions) {
    this.options = {
      sampleRate: 16000,
      channels: 1,
      ...options
    };
  }

  async start(): Promise<void> {
    if (this.isRecording) {
      console.warn('Audio recorder is already recording, ignoring start request');
      return;
    }

    try {
      // Import audioDeviceManager dynamically to avoid circular dependencies
      const { audioDeviceManager } = await import('./audio-devices');
      
      // Get media stream from the selected device using the device manager
      this.mediaStream = await audioDeviceManager.getDeviceStream(this.options.deviceId);
      
      if (!this.mediaStream) {
        throw new Error('Failed to get media stream from device');
      }

      // Create audio context
      this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({
        sampleRate: this.options.sampleRate
      });

      // Create source node from media stream
      this.sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);

      // Create a ScriptProcessorNode for raw audio processing
      const bufferSize = 4096; // Can be 256, 512, 1024, 2048, 4096, 8192, 16384
      this.scriptNode = this.audioContext.createScriptProcessor(bufferSize, 1, 1);

      this.scriptNode.onaudioprocess = (event: AudioProcessingEvent) => {
        if (!this.isRecording) return;
        
        // Get the raw audio data from the input buffer
        const inputData = event.inputBuffer.getChannelData(0);
        
        // The data is already a Float32Array, so we can pass it directly
        if (this.options.onData) {
          this.options.onData(inputData);
        }
      };

      // Connect the nodes
      this.sourceNode.connect(this.scriptNode);
      this.scriptNode.connect(this.audioContext.destination); // Connect to destination to start processing

      this.isRecording = true;

      if (this.options.onStart) {
        this.options.onStart();
      }

    } catch (error) {
      if (this.options.onError) {
        this.options.onError(error as Error);
      }
      throw error;
    }
  }

  async stop(): Promise<void> {
    if (!this.isRecording) return;

    this.isRecording = false;

    // Disconnect and cleanup
    if (this.scriptNode) {
      this.scriptNode.disconnect();
      this.scriptNode.onaudioprocess = null;
      this.scriptNode = null;
    }

    if (this.sourceNode) {
      this.sourceNode.disconnect();
      this.sourceNode = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(track => track.stop());
      this.mediaStream = null;
    }

    if (this.audioContext) {
      await this.audioContext.close();
      this.audioContext = null;
    }

    // Add a small delay to ensure resources are fully released
    await new Promise(resolve => setTimeout(resolve, 100));

    if (this.options.onStop) {
      this.options.onStop();
    }
  }

  isActive(): boolean {
    return this.isRecording;
  }

  // Convert Float32Array to Int16Array for server transmission
  static float32ToInt16(float32Array: Float32Array): Int16Array {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return int16Array;
  }

  // Convert Int16Array to Float32Array
  static int16ToFloat32(int16Array: Int16Array): Float32Array {
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 0x7FFF;
    }
    return float32Array;
  }

  // Get current audio level for visualization
  static getAudioLevel(audioData: Float32Array): number {
    let sum = 0;
    for (let i = 0; i < audioData.length; i++) {
      sum += audioData[i] * audioData[i];
    }
    const rms = Math.sqrt(sum / audioData.length);
    return Math.min(1, rms * 10); // Scale for better visualization
  }
}
