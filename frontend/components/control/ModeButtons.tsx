import { Button } from "@/components/ui/button";
import { Type, Subtitles } from "lucide-react";

interface ModeButtonsProps {
  voiceTypingActive: boolean;
  liveSubtitleActive: boolean;
  onToggleVoiceTyping: () => void;
  onToggleLiveSubtitle: () => void;
}

export function ModeButtons({
  voiceTypingActive,
  liveSubtitleActive,
  onToggleVoiceTyping,
  onToggleLiveSubtitle,
}: ModeButtonsProps) {
  return (
    <div className="flex items-center gap-1 flex-1 justify-start no-drag-region">
      <Button
        variant="outline"
        size="sm"
        className={`px-1.5 py-1 border-slate-600 text-slate-300 hover:bg-slate-700 bg-transparent relative transition-all duration-200 min-w-[90px] no-drag-region ${
          voiceTypingActive ? "shadow-md shadow-blue-500/50 border-blue-400 text-blue-300 bg-blue-900/30" : ""
        }`}
        onClick={onToggleVoiceTyping}
      >
        <Type className="w-2.5 h-2.5 mr-0.5" />
        <span className="text-[10px]">Voice Typing</span>
        <span className="text-slate-500 text-[8px] ml-0.5">Win+Alt+V</span>
        {voiceTypingActive && (
          <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse" />
        )}
      </Button>

      <Button
        variant="outline"
        size="sm"
        className={`px-1.5 py-1 border-slate-600 text-slate-300 hover:bg-slate-700 bg-transparent relative transition-all duration-200 min-w-[90px] ${
          liveSubtitleActive
            ? "shadow-md shadow-green-500/50 border-green-400 text-green-300 bg-green-900/30"
            : ""
        }`}
        onClick={onToggleLiveSubtitle}
      >
        <Subtitles className="w-2.5 h-2.5 mr-0.5" />
        <span className="text-[10px]">Live Subtitle</span>
        <span className="text-slate-500 text-[8px] ml-0.5">Win+Alt+L</span>
        {liveSubtitleActive && (
          <div className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse" />
        )}
      </Button>
    </div>
  );
}
