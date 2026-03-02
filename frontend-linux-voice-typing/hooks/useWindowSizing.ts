import { useState, useEffect, useRef } from 'react';

export function useWindowSizing(openDropdown: 'source' | 'target' | 'audio' | null, pendingDropdown: 'source' | 'target' | 'audio' | null) {
  const [panelHeights, setPanelHeights] = useState({ toolbar: 0, settings: 0 });
  const [showSettings, setShowSettings] = useState(false);

  const rootRef = useRef<HTMLDivElement>(null);
  const toolbarRef = useRef<HTMLDivElement>(null);
  const settingsRef = useRef<HTMLDivElement>(null);
  const windowSizeRef = useRef({ width: 0, height: 0 });
  const animationTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Measure panel heights
  useEffect(() => {
    const elementsToObserve = [
      { ref: toolbarRef, key: 'toolbar' },
      { ref: settingsRef, key: 'settings' },
    ];

    const observers = elementsToObserve.map(({ ref, key }) => {
      if (!ref.current) return null;

      const observer = new ResizeObserver((entries) => {
        if (entries[0]) {
          const newHeight = Math.ceil(entries[0].target.getBoundingClientRect().height);
          setPanelHeights((prev) =>
            prev[key as keyof typeof prev] !== newHeight
              ? { ...prev, [key]: newHeight }
              : prev
          );
        }
      });

      observer.observe(ref.current);
      return observer;
    }).filter(Boolean) as ResizeObserver[];

    return () => {
      observers.forEach((observer) => observer.disconnect());
    };
  }, []);

  // Measure initial size and setup observer for width changes
  useEffect(() => {
    if (!rootRef.current) return;

    const observer = new ResizeObserver((entries) => {
      if (entries[0]) {
        const newWidth = Math.ceil(entries[0].contentRect.width);

        if (window.electronAPI && newWidth > 0 && newWidth !== windowSizeRef.current.width) {
          windowSizeRef.current.width = newWidth;

          // On first measure, set initial height as well
          if (windowSizeRef.current.height === 0) {
            let initialHeight = panelHeights.toolbar;
            windowSizeRef.current.height = initialHeight;
          }

          window.electronAPI.setWindowSize({
            width: windowSizeRef.current.width,
            height: windowSizeRef.current.height
          });
        }
      }
    });

    observer.observe(rootRef.current);

    return () => observer.disconnect();
  }, [panelHeights.toolbar]);

  // Handle settings panel padding animation
  useEffect(() => {
    if (showSettings) {
      // Immediately show padding when opening
      // Padding is handled in the component
    } else {
      // Delay hiding padding until after animation completes
      const timer = setTimeout(() => {
        // Padding hiding is handled in the component
      }, 500); // Match animation duration
      return () => clearTimeout(timer);
    }
  }, [showSettings]);

  // Handle height changes based on UI state
  useEffect(() => {
    // Don't run until initial width and toolbar height are measured
    if (windowSizeRef.current.width === 0 || panelHeights.toolbar === 0) return;

    const { toolbar, settings } = panelHeights;
    const PADDING = 8; // Corresponds to pt-2/pb-2/mb-2 (0.5rem)
    const LANGUAGE_DROPDOWN_HEIGHT = 150; // Estimated height for language dropdown items
    const AUDIO_DROPDOWN_HEIGHT = 300; // More height for audio device dropdown with categories

    let targetHeight = toolbar;
    if (showSettings) {
      targetHeight += PADDING * 2; // For pt-2 and pb-2 on the container
      targetHeight += settings;
    }
    // Add extra height when dropdown is open or pending
    if (openDropdown || pendingDropdown) {
      // Use different heights based on dropdown type
      if (openDropdown === 'audio' || pendingDropdown === 'audio') {
        targetHeight += AUDIO_DROPDOWN_HEIGHT;
      } else {
        targetHeight += LANGUAGE_DROPDOWN_HEIGHT;
      }
    }

    const currentHeight = windowSizeRef.current.height;
    if (targetHeight === currentHeight) return;

    const isExpanding = targetHeight > currentHeight;
    const width = windowSizeRef.current.width;

    if (animationTimeoutRef.current) {
      clearTimeout(animationTimeoutRef.current);
    }

    const setSize = () => {
      if (window.electronAPI) {
        window.electronAPI.setWindowSize({ width, height: targetHeight });
      }
      windowSizeRef.current.height = targetHeight;
    };

    if (isExpanding) {
      // Expand: resize window first, then animate UI
      setSize();
    } else {
      // Shrink: animate UI first, then resize window
      animationTimeoutRef.current = setTimeout(setSize, 500); // Animation duration
    }

    return () => {
      if (animationTimeoutRef.current) {
        clearTimeout(animationTimeoutRef.current);
      }
    };
  }, [showSettings, panelHeights, openDropdown, pendingDropdown]);

  const toggleSettings = () => setShowSettings(!showSettings);

  return {
    rootRef,
    toolbarRef,
    settingsRef,
    showSettings,
    toggleSettings,
  };
}
