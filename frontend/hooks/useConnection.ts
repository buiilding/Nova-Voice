import { useState, useEffect } from 'react';
import { gateway } from '@/lib/gateway';

export function useConnection() {
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [mode, setMode] = useState<'typing' | 'subtitle'>('typing');

  useEffect(() => {
    const handleConnectionStatus = (_event: any, data: { connected: boolean }) => {
      setConnected(data.connected);
      setConnecting(false);
    };

    window.electronAPI.onConnectionStatus(handleConnectionStatus);

    return () => {
      window.electronAPI.removeAllListeners('connection-status');
    };
  }, []);

  const connect = async (): Promise<{ success: boolean; error?: string }> => {
    if (connected) return { success: true };
    if (connecting) return { success: false, error: 'Already connecting' };

    setConnecting(true);
    try {
      const result = await gateway.connect();
      return result;
    } catch (error) {
      setConnecting(false);
      return { success: false, error: error instanceof Error ? error.message : 'Connection failed' };
    }
  };

  const disconnect = async () => {
    if (!connected) return;
    await gateway.disconnect();
  };

  const setModeAsync = async (newMode: 'typing' | 'subtitle') => {
    const result = await gateway.setMode(newMode);
    if (result.success) {
      setMode(newMode);
    }
    return result;
  };

  return {
    connected,
    connecting,
    mode,
    connect,
    disconnect,
    setMode: setModeAsync,
  };
}
