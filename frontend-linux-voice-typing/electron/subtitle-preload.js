const { contextBridge, ipcRenderer } = require('electron');

console.log('[SUBTITLE-PRELOAD] Preload script loaded successfully');

// Listen for subtitle text updates and apply to DOM
window.addEventListener('DOMContentLoaded', () => {
  console.log('[SUBTITLE-PRELOAD] DOMContentLoaded event fired');
  
  const ensureElements = () => {
    let container = document.getElementById('subtitle-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'subtitle-container';
      container.style.position = 'fixed';
      container.style.left = '0';
      container.style.right = '0';
      container.style.bottom = '24px';
      container.style.display = 'flex';
      container.style.flexDirection = 'column';
      container.style.alignItems = 'center';
      container.style.justifyContent = 'flex-end';
      container.style.pointerEvents = 'none';
      container.style.gap = '8px';
      document.body.appendChild(container);
    }

    // Transcription overlay (top in dual mode; bottom in single mode)
    let transcriptionBubble = document.getElementById('transcription-bubble');
    if (!transcriptionBubble) {
      transcriptionBubble = document.createElement('div');
      transcriptionBubble.id = 'transcription-bubble';
      transcriptionBubble.style.width = '760px';
      transcriptionBubble.style.background = 'rgba(0,0,0,0.85)';
      transcriptionBubble.style.border = '1px solid rgba(100,100,100,0.4)';
      transcriptionBubble.style.borderRadius = '12px';
      transcriptionBubble.style.padding = '12px 16px';
      transcriptionBubble.style.color = 'white';
      transcriptionBubble.style.fontFamily = 'Arial, sans-serif';
      transcriptionBubble.style.fontWeight = '600';
      transcriptionBubble.style.fontSize = '18px';
      transcriptionBubble.style.lineHeight = '24px';
      transcriptionBubble.style.backdropFilter = 'blur(6px)';
      transcriptionBubble.style.pointerEvents = 'none';
      transcriptionBubble.style.whiteSpace = 'nowrap';
      transcriptionBubble.style.overflow = 'hidden';
      transcriptionBubble.style.textOverflow = 'clip';
      transcriptionBubble.style.order = '1';
      transcriptionBubble.style.display = 'none'; // Hidden by default
      container.appendChild(transcriptionBubble);
    }

    // Translation overlay (bottom)
    let translationBubble = document.getElementById('translation-bubble');
    if (!translationBubble) {
      translationBubble = document.createElement('div');
      translationBubble.id = 'translation-bubble';
      translationBubble.style.width = '760px';
      translationBubble.style.background = 'rgba(59,130,246,0.9)'; // Blue background for translation
      translationBubble.style.border = '1px solid rgba(147,197,253,0.6)';
      translationBubble.style.borderRadius = '12px';
      translationBubble.style.padding = '12px 16px';
      translationBubble.style.color = 'white';
      translationBubble.style.fontFamily = 'Arial, sans-serif';
      translationBubble.style.fontWeight = '600';
      translationBubble.style.fontSize = '18px';
      translationBubble.style.lineHeight = '24px';
      translationBubble.style.backdropFilter = 'blur(6px)';
      translationBubble.style.pointerEvents = 'none';
      translationBubble.style.whiteSpace = 'nowrap';
      translationBubble.style.overflow = 'hidden';
      translationBubble.style.textOverflow = 'clip';
      translationBubble.style.order = '2';
      translationBubble.style.display = 'none'; // Hidden by default
      container.appendChild(translationBubble);
    }

    return { container, transcriptionBubble, translationBubble };
  };

  // Keep last non-empty text to avoid flicker between updates
  let lastTranscriptionText = '';
  let lastTranslationText = '';
  let currentMode = 'dual'; // 'dual' or 'single'

  // Timeout management for overlay disappearance
  const TIMEOUT_DURATION = 3000; // 3 seconds
  let transcriptionTimeout = null;
  let translationTimeout = null;
  let lastTranscriptionUpdate = 0;
  let lastTranslationUpdate = 0;

  // Function to hide transcription overlay
  const hideTranscriptionOverlay = () => {
    const transcriptionBubble = document.getElementById('transcription-bubble');
    if (transcriptionBubble) {
      transcriptionBubble.style.display = 'none';
    }
    transcriptionTimeout = null;
  };

  // Function to hide translation overlay
  const hideTranslationOverlay = () => {
    const translationBubble = document.getElementById('translation-bubble');
    if (translationBubble) {
      translationBubble.style.display = 'none';
    }
    translationTimeout = null;
  };

  // Function to reset transcription timeout
  const resetTranscriptionTimeout = () => {
    if (transcriptionTimeout) {
      clearTimeout(transcriptionTimeout);
    }
    transcriptionTimeout = setTimeout(hideTranscriptionOverlay, TIMEOUT_DURATION);
    lastTranscriptionUpdate = Date.now();
  };

  // Function to reset translation timeout
  const resetTranslationTimeout = () => {
    if (translationTimeout) {
      clearTimeout(translationTimeout);
    }
    translationTimeout = setTimeout(hideTranslationOverlay, TIMEOUT_DURATION);
    lastTranslationUpdate = Date.now();
  };

  // Function to clear all timeouts
  const clearAllTimeouts = () => {
    if (transcriptionTimeout) {
      clearTimeout(transcriptionTimeout);
      transcriptionTimeout = null;
    }
    if (translationTimeout) {
      clearTimeout(translationTimeout);
      translationTimeout = null;
    }
  };

  // Cleanup timeouts when window is unloaded
  window.addEventListener('beforeunload', clearAllTimeouts);

  // Utility: crop text to show the last 100 characters
  const cropToFitTail = (el, text) => {
    if (!text) return '';
    // Simply return the last 85 characters
    return text.slice(-85);
  };
  const setBubbleText = (bubble, text, lastTextRefSetter, isTranscription = false) => {
    const incoming = (text || '').toString();
    if (incoming.trim()) {
      const cropped = cropToFitTail(bubble, incoming);
      bubble.textContent = cropped;
      bubble.style.display = 'block';
      lastTextRefSetter(cropped);

      // Reset timeout for this bubble
      if (isTranscription) {
        resetTranscriptionTimeout();
      } else {
        resetTranslationTimeout();
      }
    } else {
      // Keep previous text visible to avoid flicker; do not hide
      bubble.style.display = bubble.textContent ? 'block' : 'none';
    }
  };

  // Handle single text updates (translation disabled)
  ipcRenderer.on('subtitle-update', (_event, text) => {
    console.log('[SUBTITLE-PRELOAD] Received subtitle-update:', text);
    const { transcriptionBubble, translationBubble } = ensureElements();
    const safe = (text || '').toString();

    currentMode = 'single';
    // Place transcription bubble at bottom in single mode
    transcriptionBubble.style.order = '2';
    translationBubble.style.order = '1';
    translationBubble.style.display = 'none';

    setBubbleText(transcriptionBubble, safe, (v) => { lastTranscriptionText = v; }, true);
    console.log('[SUBTITLE-PRELOAD] Updated transcription bubble with text:', safe);
  });

  // Handle dual text updates (transcription + translation)
  ipcRenderer.on('subtitle-update-dual', (_event, data) => {
    console.log('[SUBTITLE-PRELOAD] Received subtitle-update-dual:', data);
    const { transcriptionBubble, translationBubble } = ensureElements();

    currentMode = 'dual';
    // Ensure fixed positions: transcription on top, translation at bottom
    transcriptionBubble.style.order = '1';
    translationBubble.style.order = '2';

    const transcriptionText = (data?.transcription || '').toString();
    const translationText = (data?.translation || '').toString();

    // Update transcription: keep visible even if current update empty (avoid flicker)
    setBubbleText(transcriptionBubble, transcriptionText, (v) => { lastTranscriptionText = v; }, true);
    console.log('[SUBTITLE-PRELOAD] Updated transcription bubble:', transcriptionText);

    // Update translation: keep background and last text to simulate appending
    if (translationText.trim()) {
      setBubbleText(translationBubble, translationText, (v) => { lastTranslationText = v; }, false);
      translationBubble.style.display = 'block';
      translationBubble.style.visibility = 'visible';
      console.log('[SUBTITLE-PRELOAD] Updated translation bubble:', translationText);
    } else {
      // Keep previous text visible to avoid flicker; do not hide
      translationBubble.style.display = translationBubble.textContent ? 'block' : 'none';
      console.log('[SUBTITLE-PRELOAD] No translation text, keeping previous');
    }
  });
});

// Expose minimal API if needed later
contextBridge.exposeInMainWorld('subtitleOverlay', {
  // no-op, reserved for future
});


