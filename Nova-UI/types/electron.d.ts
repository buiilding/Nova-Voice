// Module augmentation to extend the Window interface
declare global {
  interface Window {
    electronAPI: {
      // Platform info
      platform: string;
      versions: NodeJS.ProcessVersions;

      // Window management
      setWindowSize: (size: { width: number; height: number }) => Promise<void>;
      getScreenSize: () => Promise<{ width: number; height: number }>;
      setAlwaysOnTop: (flag: boolean) => Promise<void>;
      minimize: () => Promise<void>;
      maximize: () => Promise<void>;
      close: () => Promise<void>;

      // Gateway client functionality
      connectGateway: () => Promise<void>;
      disconnectGateway: () => Promise<void>;
      sendAudioData: (audioData: Uint8Array, sampleRate: number) => Promise<void>;
      updateLanguages: (sourceLang: string, targetLang: string) => Promise<void>;
      sendStartOver: () => Promise<void>;
      getConnectionStatus: () => Promise<{ connected: boolean; clientId: string | null }>;

      // Mode switching
      setMode: (mode: string) => Promise<{ success: boolean; error?: string }>;
      getMode: () => Promise<string>;

      // Notifications
      showNotification: (title: string, message: string) => Promise<void>;

      // Event listeners
      onConnectionStatus: (event: any, data: any) => void;
      onGatewayStatus: (event: any, data: any) => void;
      onRealtimeResult: (event: any, data: any) => void;
      onUtteranceEnd: (event: any, data: any) => void;
      onLiveTranscriptionUpdate: (event: any, data: any) => void;

      // Permissions
      requestMicrophonePermission: () => Promise<void>;
      requestSystemAudioPermission: () => Promise<void>;

      // Legacy
      onMainProcessMessage: (callback: (message: string) => void) => void;
      removeAllListeners: (event: string) => void;
    };
  }
}

export {};

