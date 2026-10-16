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
    <header className="sticky top-0 z-50 bg-[#0B0D0D]/95 backdrop-blur-md border-b border-[rgba(120,160,153,0.16)] h-14 px-4 sm:px-6">
      <div className="max-w-[1500px] mx-auto h-full flex items-center justify-between gap-4">
        {/* Brand */}
        <NavLink 
          to="/"
          className="flex items-center gap-2.5 select-none shrink-0"
          onClick={() => setMobileMenuOpen(false)}
        >
          <div className="w-6 h-6 rounded-md bg-[#161B1A] border border-[rgba(120,160,153,0.3)] flex items-center justify-center text-[#36D6C8]">
            <span className="w-2 h-2 rounded-full bg-[#36D6C8]" />
          </div>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-[#F4F7F6]">
              Agentic <span className="text-[#36D6C8]">Market</span>
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#161B1A] text-[#9BA5A2] border border-[rgba(120,160,153,0.2)]">
              x402
            </span>
          </div>
        </NavLink>

        {/* Search */}
        <div className="flex-1 max-w-xs hidden md:block">
          <form onSubmit={handleSearchSubmit} className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#6B7673]" />
            <input
              type="text"
              placeholder="Search services..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0D1010] border border-[rgba(120,160,153,0.18)] rounded-md pl-8 pr-10 py-1.5 text-xs text-[#F4F7F6] placeholder-[#6B7673] focus:outline-none focus:border-[#36D6C8] font-sans transition-colors"
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2 px-1.5 py-0.5 rounded bg-[#161B1A] border border-[rgba(120,160,153,0.18)] text-[10px] font-mono text-[#6B7673]">
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
                    ? 'text-[#36D6C8] bg-[rgba(54,214,200,0.08)]'
                    : 'text-[#9BA5A2] hover:text-[#F4F7F6] hover:bg-[#161B1A]'
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
            className="px-3.5 py-1.5 rounded-md bg-[#36D6C8] hover:bg-[#45DFD2] text-[#0B0D0D] font-medium text-xs transition-colors cursor-pointer"
          >
            Get Started
          </NavLink>

          <button
            className="p-1.5 rounded-md text-[#9BA5A2] hover:text-[#36D6C8] hover:bg-[#161B1A] transition-colors border border-transparent hover:border-[rgba(120,160,153,0.2)] cursor-pointer hidden sm:block"
            title="Settings"
          >
            <SlidersHorizontal className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-1.5 rounded-md text-[#9BA5A2] hover:text-[#F4F7F6] hover:bg-[#161B1A] transition-colors lg:hidden border border-[rgba(120,160,153,0.2)]"
            aria-label="Toggle navigation"
          >
            {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden absolute top-14 left-0 right-0 bg-[#0B0D0D] border-b border-[rgba(120,160,153,0.2)] p-4 space-y-2 text-xs shadow-xl">
          <form onSubmit={handleSearchSubmit} className="relative mb-2">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#6B7673]" />
            <input
              type="text"
              placeholder="Search services..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0D1010] border border-[rgba(120,160,153,0.2)] rounded-md pl-8 pr-3 py-1.5 text-xs text-[#F4F7F6]"
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
                      ? 'text-[#36D6C8] bg-[rgba(54,214,200,0.08)]'
                      : 'text-[#9BA5A2] hover:text-[#F4F7F6] bg-[#121616]'
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
