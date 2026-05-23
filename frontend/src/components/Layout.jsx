import { NavLink, useLocation } from 'react-router-dom';
import { Outlet } from 'react-router-dom';
import {
  Camera,
  Video,
  BookOpen,
  HelpCircle,
  Settings,
  Search,
  Activity,
} from 'lucide-react';

const NAV_ITEMS = [
  { to: '/', label: 'Cam', icon: Camera },
  { to: '/video', label: 'Video', icon: Video },
  { to: '/signs', label: 'Signs', icon: BookOpen },
  { to: '/help', label: 'Help', icon: HelpCircle },
  { to: '/settings', label: 'Settings', icon: Settings },
];

/* ── Sidebar ─────────────────────────────────────────────────────────────── */

function Sidebar() {
  return (
    <aside className="flex flex-col w-[220px] min-h-full bg-surface-800 border-r border-glass-border">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-glass-border">
        <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br from-accent-500 to-accent-400 shadow-lg shadow-accent-500/25">
          <Activity size={18} className="text-white" />
        </div>
        <div>
          <h1 className="text-sm font-bold tracking-wide text-white">SignLens</h1>
          <p className="text-[10px] text-slate-400 tracking-widest uppercase">ISL Recognition</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 flex flex-col gap-1 px-3 py-4">
        {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200
              ${
                isActive
                  ? 'bg-accent-500/15 text-accent-400 shadow-sm shadow-accent-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-glass'
              }`
            }
          >
            <Icon size={18} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-glass-border">
        <p className="text-[10px] text-slate-500 text-center">v1.0.0</p>
      </div>
    </aside>
  );
}

/* ── Top Bar ─────────────────────────────────────────────────────────────── */

function TopBar() {
  const location = useLocation();
  const current = NAV_ITEMS.find(
    (item) => item.to === location.pathname
  ) ?? NAV_ITEMS[0];

  return (
    <header className="flex items-center justify-between h-14 px-6 bg-surface-800/60 backdrop-blur-md border-b border-glass-border">
      {/* Page title */}
      <h2 className="font-semibold text-white text-sm tracking-wide">
        {current.label}
      </h2>

      {/* Search + status */}
      <div className="flex items-center gap-4">
        <div className="relative">
          <Search
            size={15}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
          />
          <input
            type="text"
            placeholder="Search…"
            className="w-56 pl-9 pr-4 py-2 rounded-xl bg-surface-700 border border-glass-border text-sm text-slate-300 placeholder-slate-500 outline-none focus:border-accent-500/50 focus:ring-1 focus:ring-accent-500/25 transition-all"
          />
        </div>

        {/* User avatar */}
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-mint-400 to-accent-400 flex items-center justify-center text-xs font-bold text-white shadow-lg">
            U
          </div>
        </div>
      </div>
    </header>
  );
}

/* ── Layout ──────────────────────────────────────────────────────────────── */

export default function Layout() {
  return (
    <div className="flex h-full">
      <Sidebar />
      <div className="flex flex-col flex-1 min-w-0">
        <TopBar />
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
