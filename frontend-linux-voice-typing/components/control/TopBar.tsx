import { Button } from "@/components/ui/button";
import { Settings, RotateCcw, EyeOff, X } from "lucide-react";

interface TopBarProps {
  showSettings: boolean;
  onToggleSettings: () => void;
  onStartOver: () => void;
  onHideWindow: () => void;
  onQuitApp: () => void;
}

export function TopBar({
  showSettings,
  onToggleSettings,
  onStartOver,
  onHideWindow,
  onQuitApp,
}: TopBarProps) {
  return (
    <div className="flex items-center gap-1 flex-1 justify-end no-drag-region">
      <Button
        variant="outline"
        size="sm"
        className="px-1.5 py-1 border-slate-600 text-slate-300 hover:bg-slate-700 bg-transparent transition-all duration-200"
        onClick={onStartOver}
      >
        <RotateCcw className="w-2.5 h-2.5 mr-0.5" />
        <span className="text-[10px]">Start Over</span>
      </Button>

      <div className="flex items-center gap-0.5">
        <Button
          variant="outline"
          size="sm"
          className="px-1.5 py-1 border-slate-600 text-slate-300 hover:bg-slate-700 bg-transparent transition-all duration-200"
          onClick={onHideWindow}
        >
          <EyeOff className="w-2.5 h-2.5 mr-0.5" />
          <span className="text-[10px]">Hide</span>
          <span className="text-slate-500 text-[8px] ml-0.5">Win+Alt+H</span>
        </Button>

        <Button
          variant="ghost"
          size="sm"
          className="p-1 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-all duration-200"
          onClick={onToggleSettings}
        >
          <Settings className="w-2.5 h-2.5" />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          className="p-1 text-slate-400 hover:text-red-400 hover:bg-red-900/20 rounded-lg transition-all duration-200"
          onClick={onQuitApp}
        >
          <X className="w-2.5 h-2.5" />
        </Button>
      </div>
    </div>
  );
}
