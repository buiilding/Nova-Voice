import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface LangSelectorsProps {
  sourceLanguage: string;
  targetLanguage: string;
  onSourceLanguageChange: (lang: string) => void;
  onTargetLanguageChange: (lang: string) => void;
  openDropdown: 'source' | 'target' | 'audio' | null;
  setOpenDropdown: (dropdown: 'source' | 'target' | 'audio' | null) => void;
  setPendingDropdown: (dropdown: 'source' | 'target' | 'audio' | null) => void;
}

const languages = [
  { value: "en", label: "EN" },
  { value: "es", label: "ES" },
  { value: "fr", label: "FR" },
  { value: "de", label: "DE" },
  { value: "vi", label: "VI" },
  { value: "zh", label: "ZH" },
  { value: "ja", label: "JA" },
  { value: "hi", label: "HI" },
];

export function LangSelectors({
  sourceLanguage,
  targetLanguage,
  onSourceLanguageChange,
  onTargetLanguageChange,
  openDropdown,
  setOpenDropdown,
  setPendingDropdown,
}: LangSelectorsProps) {
  return (
    <div className="flex items-center gap-2 flex-shrink-0 no-drag-region">
      <div className="flex items-center gap-1">
        <Select
          value={sourceLanguage}
          onValueChange={onSourceLanguageChange}
          open={openDropdown === 'source'}
          onOpenChange={(open: boolean) => {
            if (open) {
              setPendingDropdown('source');
            } else {
              setOpenDropdown(null);
              setPendingDropdown(null);
            }
          }}
        >
          <SelectTrigger className="w-18 h-6 bg-slate-800/50 border-slate-600 text-white text-xs no-drag-region">
            <SelectValue placeholder="EN" />
          </SelectTrigger>
          <SelectContent className="bg-slate-800 border-slate-600">
            {languages.map((lang) => (
              <SelectItem key={lang.value} value={lang.value} className="text-white hover:bg-slate-700 text-xs">
                {lang.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-slate-400 text-[10px]">→</span>
        <Select
          value={targetLanguage}
          onValueChange={onTargetLanguageChange}
          open={openDropdown === 'target'}
          onOpenChange={(open: boolean) => {
            if (open) {
              setPendingDropdown('target');
            } else {
              setOpenDropdown(null);
              setPendingDropdown(null);
            }
          }}
        >
          <SelectTrigger className="w-18 h-6 bg-slate-800/50 border-slate-600 text-white text-xs no-drag-region">
            <SelectValue placeholder="VI" />
          </SelectTrigger>
          <SelectContent className="bg-slate-800 border-slate-600">
            {languages.map((lang) => (
              <SelectItem key={lang.value} value={lang.value} className="text-white hover:bg-slate-700 text-xs">
                {lang.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
