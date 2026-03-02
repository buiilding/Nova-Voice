// Thin wrapper around window.electronAPI for gateway operations
export const gateway = {
  connect: () => window.electronAPI.connectGateway(),
  disconnect: () => window.electronAPI.disconnectGateway(),
  sendAudio: (u8: Uint8Array, sr: number) => window.electronAPI.sendAudioData(u8, sr),
  setMode: (mode: 'typing' | 'subtitle') => window.electronAPI.setMode(mode),
  updateLanguages: (src: string, dst: string) => window.electronAPI.updateLanguages(src, dst),
  startOver: () => window.electronAPI.sendStartOver(),
};
