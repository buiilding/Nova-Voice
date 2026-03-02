import { Button } from "@/components/ui/button";
import { AudioDeviceSelector } from "@/components/audio-device-selector";
import { Settings, LogOut } from "lucide-react";

interface SettingsPanelProps {
  selectedAudioDevice: string;
  onAudioDeviceChange: (device: string) => void;
  voiceTypingKeybind: string;
  liveSubtitleKeybind: string;
  hideKeybind: string;
  onVoiceTypingKeybindChange: (keybind: string) => void;
  onLiveSubtitleKeybindChange: (keybind: string) => void;
  onHideKeybindChange: (keybind: string) => void;
  onStartOver: () => void;
}

export function SettingsPanel({
  selectedAudioDevice,
  onAudioDeviceChange,
  voiceTypingKeybind,
  liveSubtitleKeybind,
  hideKeybind,
  onVoiceTypingKeybindChange,
  onLiveSubtitleKeybindChange,
  onHideKeybindChange,
  onStartOver,
}: SettingsPanelProps) {
  return (
    <div className="bg-slate-900/70 backdrop-blur-md border border-slate-700/30 rounded-xl shadow-2xl">
      <div className="py-2 px-4">
        <div className="mb-6 flex items-center justify-between">
          <h3 className="text-white font-semibold text-lg flex items-center">
            <Settings className="w-5 h-5 mr-3" />
            Settings
          </h3>
          <Button
            variant="outline"
            size="sm"
            className="px-1.5 py-1 border-slate-600 text-slate-300 hover:bg-slate-700 bg-transparent transition-all duration-200"
            onClick={onStartOver}
          >
            <LogOut className="w-2.5 h-2.5 mr-0.5" />
            <span className="text-[10px]">Start Over</span>
          </Button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <h4 className="text-slate-300 font-medium flex items-center">
              <div className="w-4 h-4 mr-2 rounded-full bg-slate-600 flex items-center justify-center">
                <span className="text-slate-300 text-xs">🎤</span>
              </div>
              Audio Devices
            </h4>

            <div className="space-y-4">
              <div>
                <label className="text-sm text-slate-400 mb-2 block">Audio Source</label>
                <AudioDeviceSelector
                  value={selectedAudioDevice}
                  onValueChange={onAudioDeviceChange}
                  placeholder="Select audio device"
                  className="w-full"
                />
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <h4 className="text-slate-300 font-medium flex items-center">
              <div className="w-4 h-4 mr-2 rounded-full bg-slate-600 flex items-center justify-center">
                <span className="text-slate-300 text-xs">⌨️</span>
              </div>
              Keybinds
            </h4>

            <div className="space-y-4">
              <div>
                <label className="text-sm text-slate-400 mb-2 block">Voice Typing</label>
                <input
                  type="text"
                  value={voiceTypingKeybind}
                  onChange={(e) => onVoiceTypingKeybindChange(e.target.value)}
                  className="w-full h-10 px-3 bg-slate-800/50 border border-slate-600 rounded-lg text-white focus:border-blue-400 focus:outline-none transition-colors"
                  placeholder="Win+Alt+V"
                />
              </div>

              <div>
                <label className="text-sm text-slate-400 mb-2 block">Live Subtitle</label>
                <input
                  type="text"
                  value={liveSubtitleKeybind}
                  onChange={(e) => onLiveSubtitleKeybindChange(e.target.value)}
                  className="w-full h-10 px-3 bg-slate-800/50 border border-slate-600 rounded-lg text-white focus:border-blue-400 focus:outline-none transition-colors"
                  placeholder="Win+Alt+L"
                />
              </div>

              <div>
                <label className="text-sm text-slate-400 mb-2 block">Hide Window</label>
                <input
                  type="text"
                  value={hideKeybind}
                  onChange={(e) => onHideKeybindChange(e.target.value)}
                  className="w-full h-10 px-3 bg-slate-800/50 border border-slate-600 rounded-lg text-white focus:border-blue-400 focus:outline-none transition-colors"
                  placeholder="Win+Alt+H"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
