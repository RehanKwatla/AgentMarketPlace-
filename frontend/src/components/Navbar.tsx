import React, { useState } from 'react';
import { 
  Bot, 
  Search, 
  Layers, 
  Send, 
  FileText, 
  ShieldCheck, 
  HelpCircle,
  Menu,
  X,
  PlusCircle,
  Activity,
  Trophy
} from 'lucide-react';

interface NavbarProps {
  network: string;
  isHealthy: boolean;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  onOpenRegister?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  network,
  isHealthy,
  activeTab,
  setActiveTab,
  searchQuery,
  setSearchQuery,
  onOpenRegister
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { id: 'marketplace', label: 'Explore Services', icon: Layers },
    { id: 'leaderboard', label: 'Leaderboard', icon: Trophy },
    { id: 'task-console', label: 'Buyer Agent', icon: Send },
    { id: 'ledger', label: 'Payment Ledger', icon: FileText },
    { id: 'reputation', label: 'Trust & Reputation', icon: Activity },
    { id: 'seller-tools', label: 'Seller Tools', icon: ShieldCheck },
    { id: 'about', label: 'About & Docs', icon: HelpCircle }
  ];

  return (
    <header className="glass-panel sticky top-0 z-50 border-b border-slate-800/80 bg-slate-950/85 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-3">
          {/* Logo & Brand Identity */}
          <div 
            className="flex items-center gap-3 cursor-pointer select-none shrink-0"
            onClick={() => setActiveTab('marketplace')}
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 via-indigo-600 to-violet-600 flex items-center justify-center shadow-lg shadow-blue-500/20 text-white">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold tracking-tight text-white text-base">
                  Agentic <span className="text-blue-400 font-semibold">Market</span>
                </span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  x402 v2
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-sans hidden sm:block">
                Thousands of services. Zero API keys. Powered by x402.
              </p>
            </div>
          </div>

          {/* Central Search Bar with Keyboard Shortcut */}
          <div className="flex-1 max-w-md hidden md:block">
            <div className="relative">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search services, capabilities, or endpoints..."
                className="w-full bg-slate-900/90 border border-slate-800 rounded-lg pl-10 pr-12 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500/80 focus:ring-1 focus:ring-blue-500/50 font-sans transition-all"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  if (activeTab !== 'marketplace') setActiveTab('marketplace');
                }}
              />
              <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-mono text-slate-500 bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700">
                /
              </span>
            </div>
          </div>

          {/* Navigation Links - Desktop */}
          <nav className="hidden xl:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-blue-600/15 text-blue-400 border border-blue-500/30 font-semibold'
                      : 'text-slate-300 hover:text-white hover:bg-slate-900/70 border border-transparent'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Right Header CTAs & Status */}
          <div className="flex items-center gap-2.5 shrink-0">
            {/* Network Badge */}
            <div 
              className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900/80 border border-slate-800 text-[11px] font-mono"
              title={`Network Identifier: ${network} (USDC)`}
            >
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
              <span className="text-slate-300 font-medium">Base Sepolia</span>
            </div>

            {/* Health Status */}
            <div 
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900/80 border border-slate-800 text-[11px] font-mono"
              title="FastAPI Subsystem Connectivity & Readiness"
            >
              <span className={`w-1.5 h-1.5 rounded-full ${isHealthy ? 'bg-emerald-400' : 'bg-rose-500'}`} />
              <span className="text-slate-300 text-[11px]">{isHealthy ? 'CONNECTED' : 'OFFLINE'}</span>
            </div>

            {/* Get Started Button */}
            <button
              onClick={() => setActiveTab('task-console')}
              className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold font-mono uppercase tracking-wide transition-all shadow-md shadow-blue-500/20"
            >
              Get Started
            </button>

            {/* Publish Service Quick Action */}
            <button
              onClick={() => {
                if (onOpenRegister) onOpenRegister();
                else setActiveTab('seller-tools');
              }}
              className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-medium border border-slate-800 transition-colors"
            >
              <PlusCircle className="w-3.5 h-3.5 text-blue-400" />
              <span>Publish</span>
            </button>

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-900 xl:hidden border border-slate-800"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Dropdown */}
        {mobileMenuOpen && (
          <div className="xl:hidden py-3 border-t border-slate-800/80 space-y-2">
            <div className="mb-3">
              <input
                type="text"
                placeholder="Search services..."
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none"
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  if (activeTab !== 'marketplace') setActiveTab('marketplace');
                }}
              />
            </div>
            <div className="grid grid-cols-2 gap-1.5">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      setActiveTab(item.id);
                      setMobileMenuOpen(false);
                    }}
                    className={`flex items-center gap-2 p-2 rounded-lg text-xs font-medium text-left transition-colors ${
                      isActive
                        ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                        : 'text-slate-300 hover:bg-slate-900 border border-slate-800/60'
                    }`}
                  >
                    <Icon className="w-4 h-4 shrink-0" />
                    <span className="truncate">{item.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </header>
  );
};
