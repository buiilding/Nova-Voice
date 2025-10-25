const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  onAuthCallback: (callback) => ipcRenderer.on('auth-callback', callback),
  sendAuthCode: (code) => ipcRenderer.invoke('auth-callback', code),
  closeLoginWindow: () => ipcRenderer.invoke('close-login-window')
});

// Handle OAuth redirect
window.addEventListener('load', () => {
  const urlParams = new URLSearchParams(window.location.search);
  const authCode = urlParams.get('code');

  if (authCode) {
    // Send auth code to main process
    window.electronAPI.sendAuthCode(authCode);
  }
});

contextBridge.exposeInMainWorld('loginAPI', {
  submitCredentials: async (email, password) => {
    try {
      const result = await ipcRenderer.invoke('auth-login', { email, password });
      return result;
    } catch (e) {
      return { success: false, error: e?.message || 'Login failed' };
    }
  },
  openGoogleAuth: async () => {
    try {
      console.log('openGoogleAuth called');
      const result = await ipcRenderer.invoke('open-google-auth');
      console.log('IPC result:', result);
      return result;
    } catch (error) {
      console.error('Error calling open-google-auth:', error);
      return { success: false, error: error.message };
    }
  },
  openGitHubAuth: async () => {
    try {
      console.log('openGitHubAuth called');
      const result = await ipcRenderer.invoke('open-github-auth');
      console.log('IPC result:', result);
      return result;
    } catch (error) {
      console.error('Error calling open-github-auth:', error);
      return { success: false, error: error.message };
    }
  },
  openMicrosoftAuth: async () => {
    try {
      console.log('openMicrosoftAuth called');
      const result = await ipcRenderer.invoke('open-microsoft-auth');
      console.log('IPC result:', result);
      return result;
    } catch (error) {
      console.error('Error calling open-microsoft-auth:', error);
      return { success: false, error: error.message };
    }
  },
  openDiscordAuth: async () => {
    try {
      console.log('openDiscordAuth called');
      const result = await ipcRenderer.invoke('open-discord-auth');
      console.log('IPC result:', result);
      return result;
    } catch (error) {
      console.error('Error calling open-discord-auth:', error);
      return { success: false, error: error.message };
    }
  },
  googleSignIn: async () => {
    try {
      const result = await ipcRenderer.invoke('auth-google');
      return result;
    } catch (e) {
      return { success: false, error: e?.message || 'Google sign-in failed' };
    }
  },
});


