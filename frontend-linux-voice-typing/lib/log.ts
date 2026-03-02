// Minimal logger utility with debug flag support
import { config } from './config';

export const log = {
  debug: (...args: any[]) => {
    if (config.debug) {
      console.log('[DEBUG]', ...args);
    }
  },
  info: (...args: any[]) => console.log('[INFO]', ...args),
  warn: (...args: any[]) => console.warn('[WARN]', ...args),
  error: (...args: any[]) => console.error('[ERROR]', ...args),
};
