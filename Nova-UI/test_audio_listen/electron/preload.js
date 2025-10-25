const { contextBridge } = require('electron');
const path = require('path');

// Load the native audio endpoints addon
let AudioEndpointManager;
try {
  AudioEndpointManager = require('../native/index.js');
} catch (error) {
  console.warn('Native audio endpoints not available:', error.message);
  AudioEndpointManager = null;
}

contextBridge.exposeInMainWorld('electronAPI', {
  enumerateAudioEndpoints: () => {
    if (!AudioEndpointManager) {
      return { capture: [], render: [] };
    }
    try {
      const manager = new AudioEndpointManager();
      return {
        capture: manager.getCaptureDevices(),
        render: manager.getRenderDevices()
      };
    } catch (error) {
      console.error('Failed to enumerate audio endpoints:', error);
      return { capture: [], render: [] };
    }
  }
});


