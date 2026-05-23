import { Settings as SettingsIcon } from 'lucide-react';

export default function Settings() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4 p-10 rounded-2xl bg-surface-800 border border-glass-border">
        <div className="w-14 h-14 rounded-2xl bg-accent-500/10 flex items-center justify-center">
          <SettingsIcon size={28} className="text-accent-400" />
        </div>
        <h3 className="text-lg font-semibold text-white">Settings</h3>
        <p className="text-sm text-slate-400 text-center max-w-xs">
          Configure camera, model, and application preferences. Coming soon.
        </p>
      </div>
    </div>
  );
}
