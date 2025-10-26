import { AudioDeviceSelector } from "@/components/audio-device-selector";

interface AudioSourceProps {
  selectedAudioDevice: string;
  onAudioDeviceChange: (device: string) => void;
  openDropdown: 'source' | 'target' | 'audio' | null;
  setOpenDropdown: (dropdown: 'source' | 'target' | 'audio' | null) => void;
  setPendingDropdown: (dropdown: 'source' | 'target' | 'audio' | null) => void;
}

export function AudioSource({
  selectedAudioDevice,
  onAudioDeviceChange,
  openDropdown,
  setOpenDropdown,
  setPendingDropdown,
}: AudioSourceProps) {
  return (
    <div className="w-[130px]">
      <AudioDeviceSelector
        value={selectedAudioDevice}
        onValueChange={onAudioDeviceChange}
        placeholder="Select audio source"
        className="h-6 text-xs no-drag-region"
        open={openDropdown === 'audio'}
        onOpenChange={(open: boolean) => {
          if (open) {
            setPendingDropdown('audio');
          } else {
            setOpenDropdown(null);
            setPendingDropdown(null);
          }
        }}
      />
    </div>
  );
}
