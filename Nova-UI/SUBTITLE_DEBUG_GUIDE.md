# Subtitle Overlay Debug Guide

## How to View Console Logs in Packaged .exe

The packaged app includes extensive debugging logs. To see them:

### Method 1: Run from Command Line
1. Open Command Prompt or PowerShell
2. Navigate to where the .exe is installed (usually `C:\Users\YourName\AppData\Local\Programs\Nova Voice\`)
3. Run: `"Nova Voice.exe"`
4. The console will show all debug output

### Method 2: Check DevTools (if enabled)
If `ELECTRON_DEBUG=1` is set in build-env.json, you can open DevTools in the main window.

## What to Look For

### Successful Subtitle Window Creation
You should see these logs when switching to subtitle mode:
```
[SUBTITLE] Creating subtitle window...
[PRELOAD] Resolved path for subtitle-preload.js: <path>
[PRELOAD] File exists: true
[SUBTITLE] Positioned subtitle window: <width>x140 at (<x>, <y>)
[SUBTITLE] Subtitle window created successfully
[SUBTITLE] Subtitle window DOM ready, showing window
[SUBTITLE-PRELOAD] Preload script loaded successfully
[SUBTITLE-PRELOAD] DOMContentLoaded event fired
```

### Subtitle Text Updates
When transcription arrives, you should see:
```
[SUBTITLE] updateDualText called with transcription: "...", translation: "..."
[SUBTITLE] Sending subtitle-update-dual: {transcription: "...", translation: "..."}
[SUBTITLE-RENDERER] [SUBTITLE-PRELOAD] Received subtitle-update-dual: ...
[SUBTITLE-RENDERER] [SUBTITLE-PRELOAD] Updated transcription bubble: ...
```

## Common Issues

### Issue 1: Preload Script Not Found
**Symptom:** 
```
[PRELOAD] File exists: false
```

**Solution:** The preload script wasn't packaged. Check `electron-builder.json` includes `electron/**/*`.

### Issue 2: Subtitle Window Not Showing
**Symptom:** Window created but not visible

**Possible Causes:**
- Window is behind other windows (check `alwaysOnTop: true`)
- Window is transparent with no content
- Window dimensions are wrong

### Issue 3: No IPC Messages Received
**Symptom:** No `[SUBTITLE-PRELOAD] Received subtitle-update` logs

**Possible Causes:**
- Preload script didn't load
- IPC channel name mismatch
- Subtitle window was destroyed

## Testing Checklist

1. ✓ Subtitle window is created when switching to subtitle mode
2. ✓ Preload script loads successfully
3. ✓ DOM ready event fires
4. ✓ Window is positioned correctly at bottom of screen
5. ✓ IPC messages are sent from main process
6. ✓ IPC messages are received in subtitle window
7. ✓ Subtitle bubbles are created and styled
8. ✓ Text is displayed in subtitle bubbles
9. ✓ Window is visible and on top of other windows

## Manual Test

To manually test the subtitle window:

1. Start the app in subtitle mode
2. Check Task Manager to see if "Nova Voice" has multiple processes (main + subtitle window)
3. Use Win+Tab to see if subtitle window appears (it shouldn't, due to skipTaskbar)
4. Speak into microphone and verify transcription appears

## Force Visibility Test

If you want to test if the window exists but isn't showing, add this to main.js temporarily:

```javascript
// After createSubtitleWindow() in liveTranscriptionManager.start()
setTimeout(() => {
  if (subtitleWindow && !subtitleWindow.isDestroyed()) {
    console.log('[DEBUG] Subtitle window visible:', subtitleWindow.isVisible());
    console.log('[DEBUG] Subtitle window bounds:', subtitleWindow.getBounds());
    subtitleWindow.setAlwaysOnTop(true);
    subtitleWindow.show();
  }
}, 2000);
```

