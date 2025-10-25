# The Voice Typing Engine: A Deep Dive

This document provides a detailed explanation of the automatic voice typing functionality, focusing on its core engine, the `typingSimulationManager`.

## 1. High-Level Overview

The voice typing feature is designed to simulate human typing by converting real-time speech-to-text results into keyboard actions. Instead of directly inserting text into an application, it uses the system's clipboard and keyboard shortcuts (`Ctrl+Z`, `Ctrl+V`) to provide a more natural and compatible typing experience. This allows it to work with almost any text field in any application.

The entire logic for this simulation is encapsulated within the `typingSimulationManager` object in `Nova-UI/electron/main.js`.

## 2. Core Engine: `typingSimulationManager`

The `typingSimulationManager` is the brain of the operation. It runs in the Electron main process and orchestrates text processing, pasting logic, and state management.

### Key Responsibilities:
-   Maintain a queue of incoming transcription text.
-   Clean and normalize the text for consistency.
-   Decide *when* to paste text based on a set of smart rules.
-   Perform the paste operation using an "undo-and-replace" strategy.
-   Manage the lifecycle of an "utterance" to ensure proper sentence structure and spacing.

### Configuration Constants

The behavior of the engine is controlled by a few key constants:

-   `PASTE_THROTTLE_DELAY` (1.0 seconds): The minimum time that must pass between consecutive paste operations. This prevents the system from overwhelming the target application with rapid-fire updates.
-   `MIN_TEXT_LENGTH` (1 character): The minimum number of characters required to trigger a paste, if other conditions aren't met.
-   `PASTE_ON_PUNCTUATION` (true): A crucial setting that allows for immediate pasting when the transcribed text ends with a sentence-terminating punctuation mark (`.`, `!`, `?`).

## 3. The Typing Simulation Loop

The engine's heart is a worker loop that runs every 100 milliseconds.

```javascript
// A simplified view of the worker loop
function typingWorker() {
    // 1. Get the most recent text from the queue
    const newText = textQueue.shift(); 
    pendingText = newText;

    // 2. Check if it's a good time to paste
    if (shouldPasteNow(pendingText)) {
        // 3. If so, perform the paste
        pasteText(pendingText);
        pendingText = ""; // Clear the pending text
    }
}
```

This loop continuously checks for new text and decides whether to output it based on the smart pasting logic.

## 4. Text Processing and Normalization

Before any text is considered for pasting, it goes through a `preprocessText` function. This ensures that the output is clean and well-formatted.

### Pre-processing Steps:
1.  **Remove Ellipses**: Replaces `...` with nothing.
2.  **Normalize Whitespace**: Converts all tabs and newlines into single spaces.
3.  **Fix Punctuation Spacing**: Corrects common spacing errors, for example:
    -   `"hello , world"` becomes `"hello, world"`
    -   `"world !"` becomes `"world!"`
4.  **Consolidate Spaces**: Reduces multiple spaces down to a single space.
5.  **Trim**: Removes leading and trailing whitespace.

## 5. The Smart Pasting Mechanism

This is the most critical part of the system. It's not just about pasting text as soon as it arrives; it's about pasting it in a way that feels natural and doesn't disrupt the user's workflow.

### When to Paste (`shouldPasteNow`)

The decision to paste is based on three conditions, checked in order:
1.  **Throttling**: Has it been at least `1.0` second since the last paste? If not, wait. This is the primary mechanism for preventing jerky, rapid-fire updates.
2.  **Punctuation Trigger**: Does the text end with a `.`, `!`, or `?`? If so, paste immediately, bypassing the throttle. This allows for quick, responsive sentence completion.
3.  **Length Trigger**: Is the text at least `1` character long? This is a fallback to ensure that even short words or phrases are eventually pasted if they don't meet the other criteria.

### How it Pastes: The "Undo-and-Replace" Strategy (`pasteText`)

To create the illusion of evolving text (where a sentence seems to correct and complete itself), the engine uses a clever trick involving the system's undo functionality.

**Here's the sequence for a single utterance:**

1.  **First Paste**:
    -   The first piece of text for an utterance (e.g., "Hello") is written to the clipboard.
    -   The engine simulates a `Ctrl+V` keypress to paste it.
    -   The engine stores `"Hello"` in its `currentDisplayedText` variable.

2.  **Subsequent Pastes (The "Replace" part)**:
    -   The next transcription result arrives (e.g., "Hello world").
    -   The engine first simulates a `Ctrl+Z` keypress. This **undoes** the previous paste, removing "Hello" from the screen.
    -   It waits for a brief moment (50ms) to allow the operating system to process the undo command.
    -   It then writes the new, complete text ("Hello world") to the clipboard. **Note**: No additional prefix is added for subsequent text within the same utterance - the spacing between utterances is handled separately.
    -   It simulates `Ctrl+V` to paste the updated text.
    -   The engine updates its `currentDisplayedText` to `"Hello world"`.

This cycle repeats. The user sees a single piece of text that appears to grow and refine itself in place, rather than a series of appended fragments.

## 7. Utterance Spacing and Text Formatting

### Spacing Between Utterances

The system intelligently handles spacing between different utterances (speech segments separated by pauses):

- **After sentence-ending punctuation** (`.`, `!`, `?`): No extra space is added when starting a new utterance, as the punctuation already provides natural separation.
- **After non-sentence-ending text**: A single space is prepended to the first text of the new utterance to ensure proper word separation.

### Within-Utterance Text Evolution

Within a single utterance, text evolves through the "undo-and-replace" mechanism without additional spacing prefixes. This ensures that:

- "Hello" → "Hello world" → "Hello world today" appears as natural text evolution
- No extra spaces are inserted during the accumulation of text within the same thought/sentence
- The `utterancePrefix` (spacing) is only applied once at the beginning of each new utterance

### Capitalization Rules

The system handles proper capitalization between utterances by checking the last character of the previous utterance:

- **After sentence-ending punctuation (. ! ?)**: The next utterance starts with a capital letter
- **After non-sentence-ending text**: The next utterance starts with a lowercase letter (continuing the sentence flow)

**Important**: The previous utterance text is stored IMMEDIATELY (synchronously) when the final text is determined, not after the paste operation completes. This prevents race conditions where a new utterance arrives before the previous one's text has been stored, which would cause incorrect capitalization.

## 9. Managing Utterances and Pauses

The system is designed to understand the natural pauses in human speech, which correspond to the end of a thought or sentence.

### Handling New Transcriptions (`handleTranscriptionResult`)

As the STT service transcribes audio, it sends back a continuous stream of text results. The `handleTranscriptionResult` function receives these results and pushes them into the `textQueue`. To ensure responsiveness, the queue is kept very short (a maximum of 4 items), prioritizing the most recent transcription.

When the gateway detects the end of an utterance (due to a pause or hitting the maximum buffer time), it marks the final audio job with `is_final: true`. The worker processes this and sends a final transcription result that also contains this `is_final` flag. The gateway then sends the `utterance_end` signal bundled with this final result, guaranteeing that the final text arrives just before the signal to finalize the paste.

### Handling the End of an Utterance (`handleUtteranceEnd`)

The `handleUtteranceEnd` function is called when the client receives the `utterance_end` signal from the gateway. This triggers the `scheduleFinalPaste` function, which finalizes the current block of typed text.

#### `scheduleFinalPaste` Logic:
1.  **Wait and See**: It waits for `500ms`. Because the `utterance_end` signal now arrives *with* the final transcription, this delay is no longer a race condition workaround. Instead, it's a reliable grace period that ensures the final text enqueued by `handleTranscriptionResult` has time to be processed by the typing worker loop.
2.  **Final Paste**: After the delay, it performs one last paste to flush any `pendingText` and ensure the most up-to-date version of the text is on the screen.
3.  **Commit the Text**: It resets the `currentDisplayedText` variable to an empty string. This is a critical step. It "commits" the completed text so that the next utterance will start fresh and will not try to undo the text from the previous one.
4.  **Prepare for Next Utterance**: It sets a `leadingSeparator` to a single space (`" "`). This ensures that the next utterance will be separated from the previous one by a space, creating natural sentence separation.
