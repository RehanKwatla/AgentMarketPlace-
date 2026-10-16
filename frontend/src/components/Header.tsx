import React from 'react';
import { Bot, Search, ExternalLink, Settings } from 'lucide-react';

interface HeaderProps {
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onGetStarted: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  searchQuery,
  setSearchQuery,
  activeTab,
  setActiveTab,
  onGetStarted
}) => {
  return (
    <header className="sticky top-0 z-50 bg-[#171819] border-b border-[#303133] h-14 px-4 sm:px-6">
      <div className="max-w-[1600px] mx-auto h-full flex items-center justify-between gap-4">
        {/* Left: Brand Identity with Orange Robot Logo */}
        <div 
          className="flex items-center gap-3 cursor-pointer select-none shrink-0"
          onClick={() => setActiveTab('marketplace')}
        >
          <div className="w-8 h-8 rounded-lg bg-[#FF982E]/15 border border-[#FF982E]/40 flex items-center justify-center text-[#FF982E]">
            <Bot className="w-4 h-4 text-[#FF982E]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-tight text-[#F5F5F5] text-sm font-sans">
                Agentic <span className="text-[#FF982E]">Market</span>
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#303133] text-[#96989D] border border-[#303133]">
                x402
              </span>
            </div>
            <p className="text-[11px] text-[#96989D] font-mono hidden xl:block leading-none mt-0.5">
              Thousands of services. Zero API keys. Powered by x402.
            </p>
          </div>
        </div>

        {/* Center: Search input with ⌘K badge */}
        <div className="flex-1 max-w-md hidden md:block">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#96989D]" />
            <input
              type="text"
              placeholder="Find a service fast…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#101112] border border-[#303133] rounded-md pl-9 pr-12 py-1.5 text-xs text-[#F5F5F5] placeholder-[#96989D] focus:outline-none focus:border-[#FF982E] transition-colors font-mono"
            />
            <div className="absolute right-2.5 top-1/2 -translate-y-1/2 flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-[#1D1E20] border border-[#303133] text-[10px] font-mono text-[#96989D]">
              <span>⌘K</span>
            </div>
          </div>
        </div>

        {/* Right side navigation links and actions */}
        <div className="flex items-center gap-4 text-xs font-mono">
          <button
            onClick={() => setActiveTab('seller-tools')}
            className={`transition-colors hidden sm:inline ${
              activeTab === 'seller-tools' ? 'text-[#FF982E]' : 'text-[#96989D] hover:text-[#F5F5F5]'
            }`}
          >
            Seller Tools
          </button>

          <button
            onClick={() => setActiveTab('about')}
            className={`transition-colors hidden sm:inline ${
              activeTab === 'about' ? 'text-[#FF982E]' : 'text-[#96989D] hover:text-[#F5F5F5]'
            }`}
          >
            About
          </button>

          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-[#96989D] hover:text-[#F5F5F5] transition-colors"
          >
            <span>Docs</span>
            <ExternalLink className="w-3 h-3 text-[#96989D]" />
          </a>

          <button
            onClick={onGetStarted}
            className="px-3 py-1.5 rounded bg-[#FF982E] hover:bg-[#FF982E]/90 text-[#101112] font-bold text-xs uppercase tracking-wide transition-all shadow-sm shadow-[#FF982E]/30"
          >
            Get started
          </button>

          <button 
            className="p-1.5 text-[#96989D] hover:text-[#F5F5F5] transition-colors"
            title="Settings / Theme"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
