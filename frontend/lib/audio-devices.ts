 export interface AudioDevice {
  deviceId: string;
  label: string;
  kind: 'audioinput' | 'audiooutput';
  groupId?: string;
}

export interface AudioDeviceCategory {
  type: 'input' | 'output';
  label: string;
  devices: AudioDevice[];
}

export class AudioDeviceManager {
  private static instance: AudioDeviceManager;
  private devices: AudioDevice[] = [];
  private permissionGranted = false;
  private static systemAudioCaptureInProgress = false;

  private constructor() {}

  static getInstance(): AudioDeviceManager {
    if (!AudioDeviceManager.instance) {
      AudioDeviceManager.instance = new AudioDeviceManager();
    }
    return AudioDeviceManager.instance;
  }

  async requestPermission(): Promise<boolean> {
    try {
      // Request microphone permission to enumerate devices
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(track => track.stop());
      this.permissionGranted = true;
      return true;
    } catch (error) {
      console.error('Failed to get audio permission:', error);
      this.permissionGranted = false;
      return false;
    }
  }

  async enumerateDevices(): Promise<AudioDevice[]> {
    if (!this.permissionGranted) {
      const granted = await this.requestPermission();
      if (!granted) {
        return [];
      }
    }

    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      
      this.devices = devices
        .filter(device => device.kind === 'audioinput' || device.kind === 'audiooutput')
        .map(device => ({
          deviceId: device.deviceId,
          label: this.cleanDeviceLabel(device.label) || this.getDefaultDeviceName(device.kind, device.deviceId),
          kind: device.kind as 'audioinput' | 'audiooutput',
          groupId: device.groupId
        }))
        .filter(device => {
          const label = device.label.toLowerCase();
          const deviceId = device.deviceId.toLowerCase();

          // Separate filtering logic for microphones vs speakers
          if (device.kind === 'audioinput') {
            // Aggressive filtering for microphone devices - only show physical microphones
            const isVirtualMic = label.includes('virtual') ||
                                label.includes('cable') ||
                                label.includes('loopback') ||
                                label.includes('null') ||
                                label.includes('dummy') ||
                                label.includes('blackhole') ||
                                label.includes('vb-audio') ||
                                label.includes('voicemeeter') ||
                                label.includes('obs') ||
                                label.includes('streamlabs') ||
                                label.includes('xsplit') ||
                                label.includes('discord') ||
                                label.includes('zoom') ||
                                label.includes('teams') ||
                                label.includes('skype') ||
                                label.includes('slack') ||
                                label.includes('webex') ||
                                label.includes('gotomeeting') ||
                                label.includes('microsoft teams') ||
                                label.includes('google meet') ||
                                label.includes('audio repeater') ||
                                label.includes('che volume') ||
                                label.includes('jack router') ||
                                label.includes('asio') ||
                                label.includes('asio4all') ||
                                label.includes('soundflower') ||
                                label.includes('screencast') ||
                                label.includes('line in') ||
                                label.includes('wave in') ||
                                label.includes('microphone (') && (
                                  label.includes('high definition') ||
                                  label.includes('realtek') ||
                                  label.includes('conexant') ||
                                  label.includes('intel') ||
                                  label.includes('nvidia') ||
                                  label.includes('amd')
                                ) ||
                                // Filter devices with very generic or suspicious names
                                (label === 'microphone' && deviceId.length < 10) ||
                                label.includes('input') && !label.includes('microphone') ||
                                // Filter devices that appear to be system-generated duplicates
                                /^\d+$/.test(deviceId) ||
                                deviceId.startsWith('default') ||
                                deviceId.startsWith('communications');

            return !isVirtualMic;
          } else {
            // Less aggressive filtering for output devices since system audio needs some virtual devices
            const isVirtualOutput = label.includes('virtual') ||
                                   label.includes('cable') ||
                                   label.includes('loopback') ||
                                   label.includes('null') ||
                                   label.includes('dummy') ||
                                   label.includes('blackhole') ||
                                   label.includes('vb-audio') ||
                                   label.includes('voicemeeter') ||
                                   label.includes('obs') ||
                                   label.includes('streamlabs') ||
                                   label.includes('xsplit');

            return !isVirtualOutput;
          }
        });

      return this.devices;
    } catch (error) {
      console.error('Failed to enumerate audio devices:', error);
      return [];
    }
  }

  getCategorizedDevices(): AudioDeviceCategory[] {
    const inputDevices = this.devices.filter(d => d.kind === 'audioinput');
    const outputDevices = this.devices.filter(d => d.kind === 'audiooutput');

    const categories: AudioDeviceCategory[] = [];

    // Add System Audio option first (if any output devices exist)
    if (outputDevices.length > 0) {
      categories.push({
        type: 'output',
        label: 'System Audio',
        devices: [{
          deviceId: 'system-audio',
          label: 'Capture System Audio',
          kind: 'audiooutput'
        }]
      });
    }

    // Add Input Devices second
    if (inputDevices.length > 0) {
      categories.push({
        type: 'input',
        label: 'Input Devices',
        devices: inputDevices
      });
    }

    return categories;
  }

  async getDeviceStream(deviceId: string): Promise<MediaStream | null> {
    try {
      // Handle special system-audio device ID
      if (deviceId === 'system-audio') {
        // Prevent multiple simultaneous system audio capture requests
        if (AudioDeviceManager.systemAudioCaptureInProgress) {
          console.warn('System audio capture already in progress, ignoring request');
          throw new Error('Audio source is currently busy. Please wait a moment and try again.');
        }

        AudioDeviceManager.systemAudioCaptureInProgress = true;

        try {
          // On Windows Electron, rely on session.setDisplayMediaRequestHandler for loopback
          console.log('Requesting system audio capture...');
          const stream = await (navigator.mediaDevices as any).getDisplayMedia({
            video: { frameRate: 1 },
            audio: true
          });

          if (!stream.getAudioTracks || stream.getAudioTracks().length === 0) {
            // Stop the video track if no audio is available
            stream.getVideoTracks().forEach((track: MediaStreamTrack) => track.stop());
            throw new Error('No system audio track available on this OS');
          }

          console.log('System audio capture successful');
          return stream;
        } finally {
          // Reset the flag after the capture attempt (success or failure)
          AudioDeviceManager.systemAudioCaptureInProgress = false;
        }
      }

      // Handle regular devices
      const device = this.devices.find(d => d.deviceId === deviceId);
      if (!device) {
        console.error('Device not found:', deviceId);
        return null;
      }

      if (device.kind === 'audioinput') {
        // For input devices (microphones), use getUserMedia
        const constraints = {
          audio: {
            deviceId: { exact: deviceId },
            echoCancellation: false,
            noiseSuppression: false,
            autoGainControl: false
          }
        };
        return await navigator.mediaDevices.getUserMedia(constraints);
      } else {
        // Do not support selecting specific audio outputs; system audio is handled via 'system-audio'
        throw new Error('Unsupported device type for capture');
      }
    } catch (error) {
      console.error('Failed to get device stream:', error);

      // Provide more specific error messages
      const errorMessage = error instanceof Error ? error.message : String(error);
      if (errorMessage.includes('Could not start audio source')) {
        throw new Error('Audio source is currently busy. Please wait a moment and try again.');
      } else if (errorMessage.includes('Permission denied')) {
        throw new Error('Audio permission denied. Please allow microphone access.');
      } else if (errorMessage.includes('NotAllowedError')) {
        throw new Error('Audio access was denied. Please check your browser permissions.');
      }

      throw error;
    }
  }

  private getDefaultDeviceName(kind: string, deviceId: string): string {
    if (kind === 'audioinput') {
      return `Microphone ${deviceId.slice(-4)}`;
    } else {
      return `Speaker ${deviceId.slice(-4)}`;
    }
  }

  private cleanDeviceLabel(label: string): string {
    // Remove hardware IDs that appear in parentheses at the end
    // Examples: "Microphone (Razer Seiren Mini) (1532:0531)" -> "Microphone (Razer Seiren Mini)"
    // Or: "Headphones (Bluetooth) (00:11:22:33:44:55)" -> "Headphones (Bluetooth)"

    // Pattern matches: (hex digits:colons or hyphens) at the end of the string
    const hardwareIdPattern = /\s*\([0-9a-f]{4}:[0-9a-f]{4}\)$/i;
    const macAddressPattern = /\s*\([0-9a-f]{2}(?::|-)[0-9a-f]{2}(?::|-)[0-9a-f]{2}(?::|-)[0-9a-f]{2}(?::|-)[0-9a-f]{2}(?::|-)[0-9a-f]{2}\)$/i;

    let cleanedLabel = label;

    // Remove hardware IDs (like 1532:0531)
    cleanedLabel = cleanedLabel.replace(hardwareIdPattern, '');

    // Remove MAC addresses (like 00:11:22:33:44:55)
    cleanedLabel = cleanedLabel.replace(macAddressPattern, '');

    // Also remove any remaining empty parentheses at the end
    cleanedLabel = cleanedLabel.replace(/\s*\(\s*\)$/g, '');

    return cleanedLabel.trim();
  }

  // Get device information by ID
  getDeviceInfo(deviceId: string): AudioDevice | null {
    // Handle special system-audio device
    if (deviceId === 'system-audio') {
      return {
        deviceId: 'system-audio',
        label: 'Capture System Audio',
        kind: 'audiooutput'
      };
    }
    return this.devices.find(d => d.deviceId === deviceId) || null;
  }

  // Platform-specific device detection
  async detectSystemAudioDevices(): Promise<AudioDevice[]> {
    const allDevices = await this.enumerateDevices();
    
    // On different platforms, system audio capture devices might have specific names
    const systemAudioKeywords = [
      'monitor', 'loopback', 'stereo mix', 'what u hear', 'wave out mix',
      'system audio', 'desktop audio', 'speakers', 'headphones'
    ];

    return allDevices.filter(device => {
      const label = device.label.toLowerCase();
      return systemAudioKeywords.some(keyword => label.includes(keyword));
    });
  }

  // Get the default input device
  async getDefaultInputDevice(): Promise<AudioDevice | null> {
    const inputDevices = this.devices.filter(d => d.kind === 'audioinput');
    if (inputDevices.length === 0) return null;

    // Try to find a device that looks like a default microphone
    const defaultDevice = inputDevices.find(device => {
      const label = device.label.toLowerCase();
      return label.includes('default') || 
             label.includes('primary') || 
             label.includes('built-in') ||
             label.includes('internal');
    });

    return defaultDevice || inputDevices[0];
  }

  // Get the default output device
  async getDefaultOutputDevice(): Promise<AudioDevice | null> {
    const outputDevices = this.devices.filter(d => d.kind === 'audiooutput');
    if (outputDevices.length === 0) return null;

    // Try to find a device that looks like a default speaker
    const defaultDevice = outputDevices.find(device => {
      const label = device.label.toLowerCase();
      return label.includes('default') || 
             label.includes('primary') || 
             label.includes('built-in') ||
             label.includes('internal') ||
             label.includes('speakers');
    });

    return defaultDevice || outputDevices[0];
  }
}

// Export a singleton instance
export const audioDeviceManager = AudioDeviceManager.getInstance();

