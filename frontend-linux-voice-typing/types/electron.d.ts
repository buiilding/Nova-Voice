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
      hideWindow: () => Promise<void>;
      showWindow: () => Promise<void>;
      quitApp: () => Promise<void>;

      // Gateway client functionality
      connectGateway: () => Promise<{ success: boolean; error?: string }>;
      disconnectGateway: () => Promise<void>;
      sendAudioData: (audioData: Uint8Array, sampleRate: number) => Promise<void>;
      sendAudioChunk: (audioData: Uint8Array, sampleRate: number) => void;
      updateLanguages: (sourceLang: string, targetLang: string) => Promise<void>;
      sendStartOver: () => Promise<void>;
      getConnectionStatus: () => Promise<{ connected: boolean; clientId: string | null }>;

      // Mode switching
      setMode: (mode: 'typing' | 'subtitle') => Promise<{ success: boolean; error?: string }>;
      getMode: () => Promise<string>;

      // Notifications
      showNotification: (title: string, message: string) => Promise<void>;

      // Event listeners
      onConnectionStatus: (callback: (event: any, data: { connected: boolean }) => void) => void;
      onRealtimeResult: (callback: (event: any, data: any) => void) => void;
      onUtteranceEnd: (callback: (event: any, data: any) => void) => void;
      onLiveTranscriptionUpdate: (callback: (event: any, data: any) => void) => void;
      onGlobalShortcut: (callback: (event: any, action: string) => void) => void;

      // Subtitle overlay controls
      showSubtitle: () => Promise<void>;
      hideSubtitle: () => Promise<void>;
      updateSubtitle: (text: string) => void;
      updateDualSubtitle: (data: { transcription: string; translation: string }) => void;

      // Remove listeners
      removeAllListeners: (event: string) => void;
    };
  }
}

export {};

