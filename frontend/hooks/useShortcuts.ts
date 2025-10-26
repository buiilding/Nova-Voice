import { useEffect, useRef } from 'react';

export function useShortcuts(onShortcut: (action: string) => void) {
  const shortcutInProgressRef = useRef(false);

  useEffect(() => {
    const handleGlobalShortcut = async (event: any, action: string) => {
      // Prevent multiple simultaneous shortcut processing
      if (shortcutInProgressRef.current) return;
      shortcutInProgressRef.current = true;

      try {
        onShortcut(action);
      } finally {
        // Reset the flag after processing
        setTimeout(() => {
          shortcutInProgressRef.current = false;
        }, 100);
      }
    };

    if (typeof window !== 'undefined' && window.electronAPI) {
      window.electronAPI.onGlobalShortcut(handleGlobalShortcut);
    }

    return () => {
      if (typeof window !== 'undefined' && window.electronAPI) {
        window.electronAPI.removeAllListeners('global-shortcut');
      }
    };
  }, [onShortcut]);

  return {};
}
