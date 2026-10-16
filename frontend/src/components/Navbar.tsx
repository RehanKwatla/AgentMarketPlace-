import React from 'react';

interface NavbarProps {
  network: string;
  isHealthy: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({ network, isHealthy }) => {
  return (
    <header className="glass-panel sticky top-0 z-50 px-6 py-4 border-b border-slate-800">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-blue-500/20 font-bold text-lg">
            ⚡
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-tight leading-none">
              DI-06 <span className="text-blue-400 font-medium">Agent Economy</span>
            </h1>
            <p className="text-xs text-slate-400 font-mono mt-0.5">Pay-Per-Call x402 v2</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-900/80 border border-slate-800 text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse"></span>
            <span className="text-slate-300">{network}</span>
          </div>

          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-slate-900/80 border border-slate-800 text-xs font-mono">
            <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
            <span className="text-slate-300">{isHealthy ? 'HEALTHY' : 'OFFLINE'}</span>
          </div>
        </div>
      </div>
    </header>
  );
};
