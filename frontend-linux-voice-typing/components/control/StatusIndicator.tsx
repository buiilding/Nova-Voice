import { Button } from "@/components/ui/button";
import { Activity } from "lucide-react";

interface StatusIndicatorProps {
  running: boolean;
  connected: boolean;
  listening: boolean;
}

export function StatusIndicator({ running, connected, listening }: StatusIndicatorProps) {
  const getStatusInfo = () => {
    if (running && connected && listening) {
      return {
        text: "Listening",
        color: "text-green-400",
        bgColor: "bg-green-900/30",
        borderColor: "border-green-400",
      };
    } else if (running && connected) {
      return {
        text: "Listening",
        color: "text-yellow-400",
        bgColor: "bg-yellow-900/30",
        borderColor: "border-yellow-400",
      };
    } else if (running && !connected) {
      return {
        text: "Connecting",
        color: "text-yellow-400",
        bgColor: "bg-yellow-900/30",
        borderColor: "border-yellow-400",
      };
    } else if (connected) {
      return {
        text: "Connected",
        color: "text-blue-400",
        bgColor: "bg-blue-900/30",
        borderColor: "border-blue-400",
      };
    } else {
      return {
        text: "Inactive",
        color: "text-slate-400",
        bgColor: "bg-slate-800/30",
        borderColor: "border-slate-600",
      };
    }
  };

  const statusInfo = getStatusInfo();

  return (
    <div className="flex items-center justify-center flex-shrink-0 no-drag-region">
      <Button
        variant="outline"
        size="sm"
        className={`px-1.5 py-1 w-[105px] ${statusInfo.borderColor} ${statusInfo.color} hover:bg-slate-700 ${statusInfo.bgColor} transition-all duration-200`}
      >
        <Activity className="w-2.5 h-2.5 mr-0.5" />
        <span className="text-[10px]">{statusInfo.text}</span>
      </Button>
    </div>
  );
}
