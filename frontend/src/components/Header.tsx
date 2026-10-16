import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { 
  Search, 
  Layers, 
  Send, 
  Coins, 
  ShieldCheck, 
  BarChart3, 
  HelpCircle, 
  BookOpen, 
  Menu, 
  X,
  SlidersHorizontal
} from 'lucide-react';
import { useMarketplace } from '../context/MarketplaceContext';

export const Header: React.FC = () => {
  const { searchQuery, setSearchQuery } = useMarketplace();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate('/marketplace');
    }
  };

  const navLinks = [
    { to: '/marketplace', label: 'Marketplace', icon: Layers },
    { to: '/payments', label: 'Payments', icon: Coins },
    { to: '/buyer', label: 'Buyer Agent', icon: Send },
    { to: '/seller', label: 'Seller Tools', icon: ShieldCheck },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
    { to: '/about', label: 'About', icon: HelpCircle },
    { to: '/docs', label: 'Docs', icon: BookOpen },
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#0A0A0A]/95 backdrop-blur-md border-b border-[rgba(255, 255, 255,0.16)] h-14 px-4 sm:px-6">
      <div className="max-w-[1500px] mx-auto h-full flex items-center justify-between gap-4">
        {/* Brand */}
        <NavLink 
          to="/"
          className="flex items-center gap-2.5 select-none shrink-0"
          onClick={() => setMobileMenuOpen(false)}
        >
          <div className="w-6 h-6 rounded-md bg-[#171717] border border-[rgba(255, 255, 255,0.3)] flex items-center justify-center text-[#FFFFFF]">
            <span className="w-2 h-2 rounded-full bg-[#FFFFFF]" />
          </div>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-[#FAFAFA]">
              Agentic <span className="text-[#FFFFFF]">Market</span>
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#171717] text-[#A3A3A3] border border-[rgba(255, 255, 255,0.2)]">
              x402
            </span>
          </div>
        </NavLink>

        {/* Search */}
        <div className="flex-1 max-w-xs hidden md:block">
          <form onSubmit={handleSearchSubmit} className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#737373]" />
            <input
              type="text"
              placeholder="Search services..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.18)] rounded-md pl-8 pr-10 py-1.5 text-xs text-[#FAFAFA] placeholder-[#737373] focus:outline-none focus:border-[#FFFFFF] font-sans transition-colors"
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2 px-1.5 py-0.5 rounded bg-[#171717] border border-[rgba(255, 255, 255,0.18)] text-[10px] font-mono text-[#737373]">
              ⌘K
            </div>
          </form>
        </div>

        {/* Nav Links */}
        <nav className="hidden lg:flex items-center gap-1 text-[13px]">
          {navLinks.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `px-3 py-1.5 rounded-md transition-colors font-medium ${
                  isActive
                    ? 'text-[#FFFFFF] bg-[rgba(255, 255, 255,0.08)]'
                    : 'text-[#A3A3A3] hover:text-[#FAFAFA] hover:bg-[#171717]'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* CTA */}
        <div className="flex items-center gap-2.5">
          <NavLink
            to="/buyer"
            className="px-3.5 py-1.5 rounded-md bg-[#FFFFFF] hover:bg-[#E5E5E5] text-[#0A0A0A] font-medium text-xs transition-colors cursor-pointer"
          >
            Get Started
          </NavLink>

          <button
            className="p-1.5 rounded-md text-[#A3A3A3] hover:text-[#FFFFFF] hover:bg-[#171717] transition-colors border border-transparent hover:border-[rgba(255, 255, 255,0.2)] cursor-pointer hidden sm:block"
            title="Settings"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-1.5 rounded-md text-[#A3A3A3] hover:text-[#FAFAFA] hover:bg-[#171717] transition-colors lg:hidden border border-[rgba(255, 255, 255,0.2)]"
            aria-label="Toggle navigation"
          >
            {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden absolute top-14 left-0 right-0 bg-[#0A0A0A] border-b border-[rgba(255, 255, 255,0.2)] p-4 space-y-2 text-xs shadow-xl">
          <form onSubmit={handleSearchSubmit} className="relative mb-2">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#737373]" />
            <input
              type="text"
              placeholder="Search services..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0D0D0D] border border-[rgba(255, 255, 255,0.2)] rounded-md pl-8 pr-3 py-1.5 text-xs text-[#FAFAFA]"
            />
          </form>

          <div className="grid grid-cols-2 gap-1.5">
            {navLinks.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setMobileMenuOpen(false)}
                className={({ isActive }) =>
                  `p-2 rounded-md flex items-center gap-2 font-medium ${
                    isActive
                      ? 'text-[#FFFFFF] bg-[rgba(255, 255, 255,0.08)]'
                      : 'text-[#A3A3A3] hover:text-[#FAFAFA] bg-[#121212]'
                  }`
                }
              >
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        </div>
      )}
    </header>
  );
};
