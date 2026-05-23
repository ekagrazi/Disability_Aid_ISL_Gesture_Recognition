import { HelpCircle } from 'lucide-react';

export default function Help() {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="flex flex-col items-center gap-4 p-10 rounded-2xl bg-surface-800 border border-glass-border">
        <div className="w-14 h-14 rounded-2xl bg-accent-500/10 flex items-center justify-center">
          <HelpCircle size={28} className="text-accent-400" />
        </div>
        <h3 className="text-lg font-semibold text-white">Help & Guides</h3>
        <p className="text-sm text-slate-400 text-center max-w-xs">
          Tutorials, FAQs, and troubleshooting for the ISL Recognition App. Coming soon.
        </p>
      </div>
    </div>
  );
}
