const { AudioEndpoints } = require('./build/Release/audio_endpoints');

class AudioEndpointManager {
  constructor() {
    this.endpoints = new AudioEndpoints();
  }

  enumerateEndpoints() {
    try {
      return this.endpoints.enumerateEndpoints();
    } catch (error) {
      console.error('Failed to enumerate audio endpoints:', error);
      return [];
    }
  }

  getCaptureDevices() {
    const allDevices = this.enumerateEndpoints();
    return allDevices.filter(device => device.flow === 'capture');
  }

  getRenderDevices() {
    const allDevices = this.enumerateEndpoints();
    return allDevices.filter(device => device.flow === 'render');
  }
}

module.exports = AudioEndpointManager;
