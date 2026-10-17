import React, { useState, useEffect } from 'react';
import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { 
  Search, 
  LayoutDashboard,
  Layers, 
  Send, 
  PlayCircle,
  Coins, 
  CheckCircle2, 
  FileText, 
  Menu, 
  X,
  Sparkles
} from 'lucide-react';

import { useMarketplace } from '../context/MarketplaceContext';
import { ProfileMenu } from './ui/ProfileMenu';

export const Header: React.FC = () => {
  const { searchQuery, setSearchQuery } = useMarketplace();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      setMobileMenuOpen(false);
      navigate('/marketplace');
    }
  };

  // Close mobile menu on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && mobileMenuOpen) {
        setMobileMenuOpen(false);
      }
    };
    if (mobileMenuOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [mobileMenuOpen]);

  // Close mobile menu on location change
  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const navLinks = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/marketplace', label: 'Marketplace', icon: Layers },
    { to: '/buyer', label: 'Buyer Console', icon: Send },
    { to: '/execution', label: 'Agent Execution', icon: PlayCircle },
    { to: '/payments', label: 'Payment Processing', icon: Coins },
    { to: '/results', label: 'Results', icon: CheckCircle2 },
    { to: '/ledger', label: 'Ledger', icon: FileText },
  ];

  return (
    <header className="sticky top-0 z-50 bg-[#F7F4EE]/95 backdrop-blur-md border-b border-[#CFC7BB] h-14 px-4 sm:px-6">
      <div className="max-w-[1600px] mx-auto h-full flex items-center justify-between gap-4">
        {/* 1. Left: Brand / Logo - Accessible & Clickable */}
        <NavLink 
          to="/dashboard"
          aria-label="Agentica Economy - Return to Dashboard"
          className="flex items-center gap-2.5 select-none shrink-0 focus-visible:ring-2 focus-visible:ring-[#7D292D] outline-none rounded-lg p-0.5"
          onClick={() => setMobileMenuOpen(false)}
        >
          <div className="w-8 h-8 rounded-lg bg-[#7D292D] border border-[#612024] flex items-center justify-center text-[#F7F4EE] shadow-sm">
            <span className="w-2.5 h-2.5 rounded-full bg-[#D7DED1] shadow-sm" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-serif font-bold text-base tracking-tight text-[#241B19]">
                Agentica <span className="text-[#7D292D]">Economy</span>
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-[#DED8CD] text-[#241B19] border border-[#CFC7BB]">
                x402 v2
              </span>
            </div>
            <span className="text-[10px] text-[#82786F] hidden md:block font-mono">
              Pay-per-Call Autonomous Agent Economy
            </span>
          </div>
        </NavLink>

        {/* 2. Middle: Navigation Items across the top */}
        <nav aria-label="Primary Navigation" className="hidden xl:flex items-center gap-1 text-xs">
          {navLinks.map((item) => {
            const isActive = location.pathname.startsWith(item.to);
            const Icon = item.icon;

            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={`px-3 py-1.5 rounded-lg transition-all font-medium flex items-center gap-1.5 focus-visible:ring-2 focus-visible:ring-[#7D292D] outline-none ${
                  isActive
                    ? 'text-[#F7F4EE] bg-[#7D292D] font-semibold shadow-sm'
                    : 'text-[#82786F] hover:text-[#241B19] hover:bg-[#DED8CD]/60 border border-transparent'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* 3. Right: Landing Button + Search + Quick Action + Profile/Avatar Menu */}
        <div className="flex items-center gap-2.5 shrink-0">
          {/* Quick Landing Page Switcher */}
          <NavLink
            to="/"
            title="View Interactive Landing Page"
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold text-[#7D292D] bg-[#7D292D]/10 hover:bg-[#7D292D] hover:text-[#F7F4EE] border border-[#7D292D]/25 transition-all shadow-xs cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Landing</span>
          </NavLink>
          {/* Quick Search */}
          <div className="hidden md:block w-44 lg:w-56">
            <form onSubmit={handleSearchSubmit} className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#82786F]" />
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[#FFFFFF] border border-[#CFC7BB] rounded-lg pl-8 pr-7 py-1 text-xs text-[#241B19] placeholder-[#82786F] focus:outline-none focus:border-[#7D292D] focus:ring-1 focus:ring-[#7D292D] font-sans transition-colors shadow-sm"
              />
              <span className="absolute right-2 top-1/2 -translate-y-1/2 text-[10px] font-mono text-[#82786F]">
                /
              </span>
            </form>
          </div>

          {/* Wireframe Profile/Avatar Menu on the Right */}
          <ProfileMenu />

          {/* Mobile hamburger menu button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-navigation-menu"
            aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            className="p-1.5 rounded-lg text-[#82786F] hover:text-[#241B19] hover:bg-[#DED8CD] transition-colors xl:hidden border border-[#CFC7BB] focus-visible:ring-2 focus-visible:ring-[#7D292D] outline-none cursor-pointer"
          >
            {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Mobile Navigation Drawer */}
      {mobileMenuOpen && (
        <div 
          id="mobile-navigation-menu"
          role="navigation"
          aria-label="Mobile Navigation"
          className="xl:hidden absolute top-14 left-0 right-0 bg-[#F7F4EE] border-b border-[#CFC7BB] p-4 space-y-3 text-xs shadow-xl z-50 animate-in fade-in slide-in-from-top-2 duration-150"
        >
          <form onSubmit={handleSearchSubmit} className="relative mb-2">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#82786F]" />
            <input
              type="text"
              placeholder="Search services, category..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#FFFFFF] border border-[#CFC7BB] rounded-lg pl-8 pr-3 py-2 text-xs text-[#241B19]"
            />
          </form>

          <div className="grid grid-cols-2 gap-1.5">
            {navLinks.map((item) => {
              const isActive = location.pathname.startsWith(item.to);
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`p-2.5 rounded-lg flex items-center gap-2 font-medium focus-visible:ring-2 focus-visible:ring-[#7D292D] outline-none ${
                    isActive
                      ? 'text-[#F7F4EE] bg-[#7D292D] font-semibold shadow-sm'
                      : 'text-[#241B19] hover:text-[#7D292D] bg-[#DED8CD]/60 border border-[#CFC7BB]'
                  }`}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span className="truncate">{item.label}</span>
                </NavLink>
              );
            })}
            <NavLink
              to="/"
              onClick={() => setMobileMenuOpen(false)}
              className="p-2.5 rounded-lg flex items-center gap-2 font-medium text-[#7D292D] bg-[#7D292D]/10 border border-[#7D292D]/30 col-span-2"
            >
              <Sparkles className="w-4 h-4 shrink-0" />
              <span>View Landing Page</span>
            </NavLink>
          </div>
        </div>
      )}
    </header>
  );
};
export default Header;
